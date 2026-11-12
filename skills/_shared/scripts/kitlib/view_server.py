"""Serve the built console and the data files, on this machine only.

Bound to 127.0.0.1. ``/`` and ``/assets/...`` come from ``dist``; ``/data/<name>.json`` comes
from ``_meta/data`` and only for the names the data format defines. ``/doc/<SCOPE>/<path>`` shows
one spec document (Markdown, PDF, an image, a link file) read from that project's folder, for
the preview panel; ``/doc/`` lists the projects it can read. GET and HEAD only, no directory
listing, no path outside those folders, no dot-files, no machine files (`_meta` keeps only its
Markdown reports), a Host check against DNS rebinding, and a strict Content-Security-Policy on
every answer.
"""

from __future__ import annotations

import http.server
import json
import re
import socketserver
from pathlib import Path
from urllib.parse import unquote

from kitlib import dataformat

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
    "connect-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'none'"
)
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}
DOC_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".url": "text/plain; charset=utf-8",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
# A script inside an SVG would run in this origin when the file is opened on its own.
SANDBOX = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src 'self'"
# The browser's own viewer draws a PDF, and Chrome refuses one served under a sandbox policy.
FRAMED = "frame-ancestors 'self'"
DOC_MAX = 25 * 1024 * 1024
DOC_SKIP = {"console", "node_modules", "_shared"}
DATA_NAMES = {f"{name}.json" for name in (*dataformat.KINDS, dataformat.INDEX)}
ASSET = re.compile(r"^assets/[\w.-]+$")


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "specwright-view"
    sys_version = ""
    dist: Path
    data: Path
    docs: dict[str, Path]
    allowed_hosts: set[str]

    def log_message(self, fmt: str, *args) -> None:  # quiet by default
        return

    def _send(
        self,
        status: int,
        body: bytes = b"",
        kind: str = "text/plain; charset=utf-8",
        head: bool = False,
        policy: str = CSP,
        size: int | None = None,
        inline: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body) if size is None else size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", policy)
        if inline:
            self.send_header("Content-Disposition", "inline")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if status == 405:
            self.send_header("Allow", "GET, HEAD")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _file(self, root: Path, rel: str, head: bool) -> None:
        path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            self._send(404, b"not found", head=head)
            return
        kind = TYPES.get(path.suffix)
        if kind is None:
            self._send(404, b"not found", head=head)
            return
        self._send(200, path.read_bytes(), kind, head)

    def _doc(self, target: str, head: bool) -> None:
        """One document of one project, or the list of projects that can be read."""
        rest = target[len("/doc/") :]
        if not rest:
            body = json.dumps({"scopes": sorted(self.docs)}).encode()
            self._send(200, body, TYPES[".json"], head)
            return
        scope, _, relative = unquote(rest).partition("/")
        path = doc_path(self.docs.get(scope), relative)
        if path is None:
            self._send(404, b"not found", head=head)
            return
        size = path.stat().st_size
        if size > DOC_MAX:
            self._send(413, b"too large", head=head)
            return
        suffix = path.suffix.lower()
        policy = {".pdf": FRAMED, ".svg": SANDBOX}.get(suffix, CSP)
        body = b"" if head else path.read_bytes()
        self._send(200, body, DOC_TYPES[suffix], head, policy, size, suffix in (".pdf", ".svg"))

    def _serve(self, head: bool) -> None:
        if self.headers.get("Host", "") not in self.allowed_hosts:
            self._send(403, b"forbidden host", head=head)
            return
        target = self.path.split("?", 1)[0].split("#", 1)[0]
        if target in ("/", "/index.html"):
            self._file(self.dist, "index.html", head)
        elif target == "/doc" or target.startswith("/doc/"):
            if self.docs:
                self._doc(target if target != "/doc" else "/doc/", head)
            else:
                self._send(404, b"not found", head=head)
        elif target.startswith("/data/"):
            name = target[len("/data/") :]
            if name in DATA_NAMES:
                self._file(self.data, name, head)
            else:
                self._send(404, b"not found", head=head)
        elif ASSET.match(target.lstrip("/")):
            self._file(self.dist, target.lstrip("/"), head)
        else:
            self._send(404, b"not found", head=head)

    def do_GET(self) -> None:  # noqa: N802
        self._serve(False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(True)

    def _refuse(self) -> None:
        self._send(405, b"method not allowed")

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _refuse  # noqa: N815


def doc_path(base: Path | None, relative: str) -> Path | None:
    """The file a document URL names inside one project folder, or None when it may not be shown."""
    if base is None or not relative or "\x00" in relative or "\\" in relative:
        return None
    parts = relative.split("/")
    if relative.startswith("/") or any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        return None
    if parts[0] in DOC_SKIP:
        return None
    if parts[0] == "_meta" and (len(parts) != 2 or parts[1].count(".") != 1):
        return None
    if Path(relative).suffix.lower() not in DOC_TYPES:
        return None
    root = base.resolve()
    path = (root / relative).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(
    dist: Path,
    data: Path,
    port: int = 4173,
    tries: int = 20,
    docs: dict[str, Path] | None = None,
) -> Server:
    """A server on 127.0.0.1, on ``port`` or the next free one.

    ``docs`` maps each project to the folder its documents are read from; without it `/doc/`
    answers 404 and the console shows only the data.
    """
    last: OSError | None = None
    for candidate in range(port, port + tries):
        handler = type("BoundHandler", (Handler,), {})
        handler.dist, handler.data = dist, data
        handler.docs = dict(docs or {})
        handler.allowed_hosts = {f"127.0.0.1:{candidate}", f"localhost:{candidate}"}
        try:
            return Server(("127.0.0.1", candidate), handler)
        except OSError as exc:
            last = exc
    raise OSError(f"no free port from {port} to {port + tries - 1}: {last}")
