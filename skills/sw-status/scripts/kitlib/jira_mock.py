"""An offline HTTP double that stores actual JSON, including ADF descriptions.

Use MockJira as a context manager. inject(method, path, failure) queues one failure:
forbidden, rate-limit, drop-after-create, drop-before-create, or concurrent-edit.
CLI exits 0 after serving until interrupted, 2 on invalid arguments.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import re
import socket
import sys
import threading
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class MockJira:
    def __init__(self, *, page_size=1):
        self.issues, self.properties = {}, {}
        self.comments, self.changelog = defaultdict(list), defaultdict(list)
        self.links, self.attachments, self.requests = [], [], []
        self.failures = defaultdict(deque)
        self.page_size = page_size
        self._clock = 0
        self._lock = threading.RLock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                # HTTP diagnostics must not disclose Authorization headers.
                pass

            def do_GET(self):
                owner._handle(self)

            def do_POST(self):
                owner._handle(self)

            def do_PUT(self):
                owner._handle(self)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = None
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        if self.thread:
            self.server.shutdown()
            self.thread.join(timeout=5)
        self.server.server_close()

    def stamp(self):
        self._clock += 1
        return f"2026-01-01T00:00:00.{self._clock:06d}+0000"

    def seed(self, key, fields):
        with self._lock:
            fields = copy.deepcopy(fields)
            fields.setdefault("updated", self.stamp())
            self.issues[key] = {"id": str(len(self.issues) + 1), "key": key, "fields": fields}
            return copy.deepcopy(self.issues[key])

    def inject(self, method, path, failure):
        if failure not in {
            "forbidden",
            "rate-limit",
            "drop-after-create",
            "drop-before-create",
            "concurrent-edit",
        }:
            raise ValueError("unknown mock failure")
        self.failures[(method, path)].append(failure)

    def _handle(self, handler):
        with self._lock:
            self._dispatch(handler)

    def _dispatch(self, handler):
        split = urlsplit(handler.path)
        path = split.path.removeprefix("/rest/api/3/")
        query = parse_qs(split.query)
        method = handler.command
        body = handler.rfile.read(int(handler.headers.get("Content-Length", "0")))
        self.requests.append({"method": method, "path": path, "body": body})

        def send(code, value=None, headers=None):
            payload = json.dumps(value).encode() if value is not None else b""
            handler.send_response(code)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(payload)))
            for name, value in (headers or {}).items():
                handler.send_header(name, value)
            handler.end_headers()
            handler.wfile.write(payload)

        def drop():
            handler.close_connection = True
            with contextlib.suppress(OSError):
                handler.connection.shutdown(socket.SHUT_RDWR)
            handler.connection.close()

        failure = self.failures[(method, path)].popleft() if self.failures[(method, path)] else None
        if failure == "forbidden":
            send(403, {})
            return
        if failure == "rate-limit":
            send(429, {}, {"Retry-After": "2"})
            return
        if failure == "drop-before-create":
            drop()
            return
        try:
            data = (
                json.loads(body)
                if body and "application/json" in handler.headers.get("Content-Type", "")
                else {}
            )
        except ValueError:
            send(400, {})
            return
        if path == "issue" and method == "POST":
            fields = data["fields"]
            project = fields.get("project", {}).get("key", "TEST")
            number = 1
            while f"{project}-{number}" in self.issues:
                number += 1
            issue = self.seed(f"{project}-{number}", fields)
            if failure == "drop-after-create":
                drop()
                return
            send(201, {"id": issue["id"], "key": issue["key"]})
            return
        if path == "search/jql" and method == "POST":
            project = re.search(r'project\s*=\s*"?([A-Za-z0-9_]+)', data["jql"], re.I)[1]
            label_match = re.search(r'labels\s*=\s*"((?:\\.|[^"\\])*)"', data["jql"], re.I)
            label = json.loads('"' + label_match[1] + '"') if label_match else None
            issues = [
                copy.deepcopy(v)
                for k, v in sorted(self.issues.items())
                if k.startswith(project + "-")
                and (label is None or label in v["fields"].get("labels", []))
            ]
            start = int(data.get("nextPageToken", 0))
            last = start + self.page_size >= len(issues)
            page = {"issues": issues[start : start + self.page_size], "isLast": last}
            if not last:
                page["nextPageToken"] = str(start + self.page_size)
            send(200, page)
            return
        if path == "issueLink" and method == "POST":
            self.links.append(copy.deepcopy(data))
            send(201)
            return
        parts = [unquote(p) for p in path.split("/")]
        if len(parts) < 2 or parts[0] != "issue" or parts[1] not in self.issues:
            send(404, {})
            return
        key = parts[1]
        issue = self.issues[key]
        if failure == "concurrent-edit":
            issue["fields"]["updated"] = self.stamp()
        if len(parts) == 2:
            if method == "GET":
                send(200, issue)
            elif method == "PUT":
                issue["fields"].update(copy.deepcopy(data["fields"]))
                issue["fields"]["updated"] = self.stamp()
                send(204)
            else:
                send(405, {})
            return
        resource = parts[2]
        if resource in {"comment", "changelog"} and method == "GET":
            items = self.comments[key] if resource == "comment" else self.changelog[key]
            start = int(query.get("startAt", ["0"])[0])
            send(
                200,
                {
                    "startAt": start,
                    "maxResults": self.page_size,
                    "total": len(items),
                    "isLast": start + self.page_size >= len(items),
                    "comments" if resource == "comment" else "values": items[
                        start : start + self.page_size
                    ],
                },
            )
            return
        if resource == "properties" and len(parts) == 4:
            prop = (key, parts[3])
            if method == "PUT":
                self.properties[prop] = copy.deepcopy(data)
                send(204)
            elif prop in self.properties:
                send(200, {"key": parts[3], "value": self.properties[prop]})
            else:
                send(404, {})
            return
        if resource == "attachments" and method == "POST":
            if handler.headers.get("X-Atlassian-Token") != "no-check" or b'name="file"' not in body:
                send(400, {})
                return
            self.attachments.append({"key": key, "body": body})
            send(200, [{"id": str(len(self.attachments))}])
            return
        send(404, {})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-size", type=int, default=1)
    args = parser.parse_args(argv)
    if args.page_size < 1:
        parser.error("page size must be positive")
    with MockJira(page_size=args.page_size) as mock:
        print(json.dumps({"site": mock.url}), flush=True)
        with contextlib.suppress(KeyboardInterrupt):
            mock.thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
