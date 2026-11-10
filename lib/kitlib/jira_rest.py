"""Small Jira Cloud v3 adapter; credentials are never included in diagnostics.

Environment: SPECWRIGHT_JIRA_SITE, SPECWRIGHT_JIRA_EMAIL, SPECWRIGHT_JIRA_TOKEN.
CLI is read-only: exits 0 success, 2 invalid configuration, 3 remote failure.
"""

from __future__ import annotations

import argparse
import base64
import email.utils
import http.client
import json
import mimetypes
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request

_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "kitlib").is_dir() or (_base / "lib" / "kitlib").is_dir():
        sys.path.insert(0, str(_base if (_base / "kitlib").is_dir() else _base / "lib"))
        break
from kitlib.jira_port import (  # noqa: E402
    Conflict,
    JiraError,
    NotFound,
    PermissionDenied,
    Port,
    RateLimited,
    Timeout,
)


def retry_after(value, now=None):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            stamp = email.utils.parsedate_to_datetime(value)
            return max(0.0, (stamp - (now or datetime.now(timezone.utc))).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 1.0


def _quote(value):
    return parse.quote(str(value), safe="")


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Redirects can leak Basic credentials to another origin.
        return None


class JiraREST(Port):
    def __init__(
        self,
        site=None,
        email=None,
        token=None,
        *,
        timeout=15,
        attachment_cap=10 * 1024 * 1024,
        max_pages=100,
        allow_http=False,
    ):
        self.site = (site or os.environ.get("SPECWRIGHT_JIRA_SITE", "")).rstrip("/")
        email = email or os.environ.get("SPECWRIGHT_JIRA_EMAIL", "")
        token = token or os.environ.get("SPECWRIGHT_JIRA_TOKEN", "")
        parts = parse.urlsplit(self.site)
        if (
            parts.scheme not in ({"http", "https"} if allow_http else {"https"})
            or not parts.netloc
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path
        ):
            raise ValueError(
                "site must be an HTTPS origin (HTTP requires explicit local testing opt-in)"
            )
        if not email or not token:
            raise ValueError("Jira email and token are required")
        if timeout <= 0 or attachment_cap < 0 or max_pages < 1:
            raise ValueError("invalid request bounds")
        self._auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode("ascii")
        self.timeout, self.attachment_cap, self.max_pages = timeout, attachment_cap, max_pages
        self._opener = request.build_opener(_NoRedirect())

    def _request(self, method, path, data=None, headers=None, raw=False):
        body = (
            data
            if raw
            else (
                json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
                if data is not None
                else None
            )
        )
        hdr = {"Authorization": self._auth, "Accept": "application/json"}
        if body is not None and not raw:
            hdr["Content-Type"] = "application/json"
        hdr.update(headers or {})
        req = request.Request(
            self.site + "/rest/api/3/" + path, data=body, headers=hdr, method=method
        )
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                payload = response.read()
                return json.loads(payload) if payload else None
        except error.HTTPError as exc:
            status = exc.code
            after = exc.headers.get("Retry-After")
            exc.close()
            if status == 404:
                raise NotFound("not found or not visible") from None
            if status in (401, 403):
                raise PermissionDenied("Jira permission denied") from None
            if status == 429:
                raise RateLimited(retry_after(after)) from None
            if status == 409:
                raise Conflict("Jira conflict") from None
            if method != "GET" and status >= 500:
                raise Timeout("server failure; write outcome unknown") from None
            raise JiraError(f"Jira HTTP {status}") from None
        except (TimeoutError, error.URLError, http.client.HTTPException, ConnectionError):
            raise Timeout("connection interrupted", ambiguous=method != "GET") from None
        except (ValueError, UnicodeError):
            if method != "GET":
                raise Timeout("invalid response; write outcome unknown") from None
            raise JiraError("invalid JSON response") from None

    def get_issue(self, key):
        return self._request("GET", "issue/" + _quote(key))

    def search_by_label(self, project, label):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project):
            raise ValueError("project must be a project key")
        if not label or any(ord(c) < 32 for c in label):
            raise ValueError("invalid label")
        escaped = label.replace("\\", "\\\\").replace('"', '\\"')
        return self.search_jql(f'project = "{project}" AND labels = "{escaped}"')

    def search_jql(self, jql):
        # Only the conservative bounded dialect is accepted; OR can escape a project bound.
        if not re.match(
            r'^\s*project\s*=\s*(?:"[A-Za-z][A-Za-z0-9_]*"|[A-Za-z][A-Za-z0-9_]*)\s*(?:AND\b|ORDER\s+BY\b|$)',
            jql,
            re.I,
        ) or re.search(r"\bOR\b", jql, re.I):
            raise ValueError("bounded JQL must begin with project = KEY and contain no OR")
        issues, token, seen = [], None, set()
        for _ in range(self.max_pages):
            payload = {"jql": jql, "maxResults": 100}
            if token:
                payload["nextPageToken"] = token
            page = self._request("POST", "search/jql", payload)
            issues.extend(page.get("issues", []))
            token = page.get("nextPageToken")
            if page.get("isLast") is True or not token:
                return issues
            if token in seen:
                raise JiraError("search pagination repeated a token")
            seen.add(token)
        raise JiraError("search pagination limit exceeded")

    def _paged(self, key, resource, field):
        items, start = [], 0
        for _ in range(self.max_pages):
            page = self._request(
                "GET",
                f"issue/{_quote(key)}/{resource}?"
                + parse.urlencode({"startAt": start, "maxResults": 100}),
            )
            chunk = page.get(field, [])
            items.extend(chunk)
            next_start = page.get("startAt", start) + len(chunk)
            if page.get("isLast") is True or next_start >= page.get("total", float("inf")):
                return items
            if not chunk or next_start <= start:
                raise JiraError("pagination made no progress")
            start = next_start
        raise JiraError("pagination limit exceeded")

    def list_changelog(self, key):
        return self._paged(key, "changelog", "values")

    def list_comments(self, key):
        return self._paged(key, "comment", "comments")

    def create_issue(self, fields):
        return self._request("POST", "issue", {"fields": fields})

    def edit_issue(self, key, fields):
        return self._request("PUT", "issue/" + _quote(key), {"fields": fields})

    def add_link(self, payload):
        return self._request("POST", "issueLink", payload)

    def attach_file(self, key, path):
        path = Path(path)
        with path.open("rb") as handle:
            data = handle.read(self.attachment_cap + 1)
        if len(data) > self.attachment_cap:
            raise ValueError("attachment exceeds configured size cap")
        filename = path.name
        if any(c in filename for c in '\r\n"\\'):
            raise ValueError("unsafe attachment filename")
        boundary = "specwright-" + uuid.uuid4().hex
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'
            ).encode()
            + data
            + f"\r\n--{boundary}--\r\n".encode()
        )
        return self._request(
            "POST",
            f"issue/{_quote(key)}/attachments",
            body,
            {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Atlassian-Token": "no-check",
            },
            raw=True,
        )

    def get_property(self, key, property_key):
        return self._request("GET", f"issue/{_quote(key)}/properties/{_quote(property_key)}")[
            "value"
        ]

    def set_property(self, key, property_key, value):
        if not property_key or len(property_key.encode()) > 255:
            raise ValueError("property key must be 1..255 bytes")
        if (
            not isinstance(value, dict)
            or len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 32768
        ):
            raise ValueError("property must be a JSON object of at most 32768 bytes")
        return self._request("PUT", f"issue/{_quote(key)}/properties/{_quote(property_key)}", value)


# Both spellings are convenient for callers without introducing a second adapter.
JiraRest = JiraREST


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key")
    args = parser.parse_args(argv)
    try:
        port = JiraREST()
        print(json.dumps(port.get_issue(args.key), ensure_ascii=False))
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except JiraError as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
