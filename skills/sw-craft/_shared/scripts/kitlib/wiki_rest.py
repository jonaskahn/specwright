"""Read-only page-tree reader for a Confluence-style wiki (REST v2), for import as evidence.

Only GET requests are made. Credentials come from SPECWRIGHT_WIKI_SITE, SPECWRIGHT_WIKI_EMAIL and
SPECWRIGHT_WIKI_TOKEN and never appear in output. Lists are walked by following the server's
`_links.next` cursor until it ends. A page limit that is reached is reported as an incomplete
pull, never as a complete one, and the received count is returned so it can be reconciled with
the expected one. Page bodies are written by program; nothing is retyped.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib import error, parse, request

API = "/wiki/api/v2"
MAX_REQUESTS = 2000
PAGE_SIZE = 100


class WikiError(Exception):
    """The wiki could not be read as asked."""


class Transport(Protocol):
    def get(self, path: str) -> dict[str, Any]: ...


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a redirect could send the credentials to another origin


class HttpTransport:
    """GET-only HTTPS transport with Basic credentials; never follows a redirect."""

    def __init__(self, site: str, email: str, token: str, timeout: float = 20) -> None:
        site = site.rstrip("/")
        parts = parse.urlsplit(site)
        if (
            parts.scheme != "https"
            or not parts.netloc
            or parts.path
            or parts.query
            or parts.fragment
        ):
            raise ValueError("site must be an HTTPS origin such as https://example.atlassian.net")
        if parts.username or parts.password:
            raise ValueError("put credentials in the environment, not in the site")
        if not email or not token:
            raise ValueError("wiki email and token are required")
        self.site, self.timeout = site, timeout
        raw = f"{email}:{token}".encode()
        self._auth = "Basic " + base64.b64encode(raw).decode("ascii")
        self._opener = request.build_opener(_NoRedirect())

    @classmethod
    def from_env(cls) -> HttpTransport:
        return cls(
            os.environ.get("SPECWRIGHT_WIKI_SITE", ""),
            os.environ.get("SPECWRIGHT_WIKI_EMAIL", ""),
            os.environ.get("SPECWRIGHT_WIKI_TOKEN", ""),
        )

    def get(self, path: str) -> dict[str, Any]:
        if not path.startswith("/wiki/"):
            raise WikiError("refusing a path outside /wiki/")
        req = request.Request(
            self.site + path,
            headers={"Authorization": self._auth, "Accept": "application/json"},
            method="GET",
        )
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                return json.loads(response.read())
        except error.HTTPError as exc:
            code = exc.code
            exc.close()
            raise WikiError(f"wiki HTTP {code}") from None
        except (TimeoutError, error.URLError, http.client.HTTPException, ConnectionError):
            raise WikiError("connection to the wiki failed") from None
        except (ValueError, UnicodeError):
            raise WikiError("the wiki returned invalid JSON") from None


@dataclass
class Page:
    id: str
    title: str
    parent_id: str
    version: str
    url: str
    body: str
    depth: int
    labels: list[str] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Pull:
    pages: list[Page]
    complete: bool
    requests: int
    note: str = ""


class Client:
    def __init__(self, transport: Transport, max_requests: int = MAX_REQUESTS) -> None:
        self.transport = transport
        self.max_requests = max_requests
        self.requests = 0

    def _get(self, path: str) -> dict[str, Any]:
        self.requests += 1
        if self.requests > self.max_requests:
            raise WikiError("request budget reached; the pull stopped")
        return self.transport.get(path)

    def paged(self, path: str) -> list[dict[str, Any]]:
        """Every result of a list, following `_links.next` until the server stops sending it."""
        joiner = "&" if "?" in path else "?"
        url: str | None = f"{path}{joiner}limit={PAGE_SIZE}"
        found: list[dict[str, Any]] = []
        seen: set[str] = set()
        while url:
            if url in seen:
                raise WikiError("the wiki repeated a page link; stopping instead of looping")
            seen.add(url)
            data = self._get(url)
            found.extend(data.get("results") or [])
            nxt = (data.get("_links") or {}).get("next")
            if nxt and not (isinstance(nxt, str) and nxt.startswith("/wiki/")):
                raise WikiError("the wiki sent a next link outside /wiki/; refusing it")
            url = nxt or None
        return found

    def page(self, page_id: str, depth: int, parent: str = "") -> Page:
        quoted = parse.quote(page_id, safe="")
        data = self._get(f"{API}/pages/{quoted}?body-format=storage")
        links = data.get("_links") or {}
        body = ((data.get("body") or {}).get("storage") or {}).get("value", "")
        base = str(links.get("base", ""))
        webui = str(links.get("webui", ""))
        return Page(
            id=str(data.get("id", page_id)),
            title=str(data.get("title", "")),
            parent_id=str(data.get("parentId") or parent or ""),
            version=f"v{(data.get('version') or {}).get('number', '?')}",
            url=(base + webui) if base.startswith("https://") and webui else "",
            body=body,
            depth=depth,
        )

    def enrich(self, page: Page, comments: bool) -> None:
        quoted = parse.quote(page.id, safe="")
        page.labels = sorted(
            str(r.get("name", ""))
            for r in self.paged(f"{API}/pages/{quoted}/labels")
            if r.get("name")
        )
        page.attachments = [
            {
                "id": str(r.get("id", "")),
                "title": str(r.get("title", "")),
                "size": r.get("fileSize", 0),
                "media_type": str(r.get("mediaType", "")),
            }
            for r in self.paged(f"{API}/pages/{quoted}/attachments")
        ]
        if comments:
            for kind in ("footer-comments", "inline-comments"):
                for r in self.paged(f"{API}/pages/{quoted}/{kind}?body-format=storage"):
                    value = ((r.get("body") or {}).get("storage") or {}).get("value", "")
                    page.comments.append({"id": str(r.get("id", "")), "kind": kind, "body": value})

    def children(self, page_id: str) -> list[dict[str, Any]]:
        quoted = parse.quote(page_id, safe="")
        found = self.paged(f"{API}/pages/{quoted}/children")
        return sorted(
            found,
            key=lambda r: (
                r.get("childPosition") or 0,
                str(r.get("title", "")).casefold(),
                str(r.get("id")),
            ),
        )

    def pull_tree(
        self, root_id: str, max_pages: int, max_depth: int, comments: bool = False
    ) -> Pull:
        """Breadth-first walk from a root page; parents come before their children."""
        if not re.fullmatch(r"\d{1,20}", root_id):
            raise ValueError("a page ID is digits only")
        pages: list[Page] = []
        queue: list[tuple[str, int, str]] = [(root_id, 0, "")]
        complete, note = True, ""
        while queue:
            page_id, depth, parent = queue.pop(0)
            if len(pages) >= max_pages:
                complete, note = False, f"stopped at {max_pages} pages; the tree is larger"
                break
            page = self.page(page_id, depth, parent)
            self.enrich(page, comments)
            pages.append(page)
            if depth >= max_depth:
                if self.children(page_id):
                    complete, note = False, f"children below depth {max_depth} were not read"
                continue
            queue.extend((str(c["id"]), depth + 1, page.id) for c in self.children(page_id))
        return Pull(pages, complete, self.requests, note)


def write_pull(pull: Pull, out_dir: Path, space: str = "wiki") -> list[dict[str, str]]:
    """Write each page body and each comment as a file; return the rows for the import list."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for page in pull.pages:
        name = f"{page.id}.html"
        (out_dir / name).write_text(page.body or "", encoding="utf-8")
        rows.append(
            {
                "path": name,
                "title": page.title,
                "source": f"wiki:{space}/{page.id}",
                "source_version": page.version,
                "remote_id": page.id,
                "parent_id": page.parent_id,
                "url": page.url,
                "labels": ",".join(page.labels),
            }
        )
        for number, comment in enumerate(page.comments, 1):
            cname = f"{page.id}-comment-{number}.html"
            (out_dir / cname).write_text(comment["body"], encoding="utf-8")
            rows.append(
                {
                    "path": cname,
                    "title": f"{page.title} comment {number}",
                    "source": f"wiki:{space}/{page.id}#{comment['kind']}-{comment['id']}",
                    "source_version": page.version,
                    "remote_id": f"{page.id}-c{comment['id']}",
                    "parent_id": page.id,
                    "url": page.url,
                    "labels": "comment",
                }
            )
    return rows
