"""Serve the built console and the data files, on this machine only.

Bound to 127.0.0.1. ``/`` and ``/assets/...`` come from ``dist``; ``/data/<name>.json`` comes
from ``_meta/data`` and only for the names the data format defines. GET and HEAD only, no
directory listing, no path outside those two folders, a Host check against DNS rebinding, and
a strict Content-Security-Policy on every answer.
"""

from __future__ import annotations

import http.server
import re
import socketserver
from pathlib import Path

from kitlib import dataformat

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'"
)
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}
DATA_NAMES = {f"{name}.json" for name in (*dataformat.KINDS, dataformat.INDEX)}
ASSET = re.compile(r"^assets/[\w.-]+$")


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "specwright-view"
    sys_version = ""
    dist: Path
    data: Path
    allowed_hosts: set[str]

    def log_message(self, fmt: str, *args) -> None:  # quiet by default
        return

    def _send(
        self,
        status: int,
        body: bytes = b"",
        kind: str = "text/plain; charset=utf-8",
        head: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CSP)
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

    def _serve(self, head: bool) -> None:
        if self.headers.get("Host", "") not in self.allowed_hosts:
            self._send(403, b"forbidden host", head=head)
            return
        target = self.path.split("?", 1)[0].split("#", 1)[0]
        if target in ("/", "/index.html"):
            self._file(self.dist, "index.html", head)
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


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(dist: Path, data: Path, port: int = 4173, tries: int = 20) -> Server:
    """A server on 127.0.0.1, on ``port`` or the next free one."""
    last: OSError | None = None
    for candidate in range(port, port + tries):
        handler = type("BoundHandler", (Handler,), {})
        handler.dist, handler.data = dist, data
        handler.allowed_hosts = {f"127.0.0.1:{candidate}", f"localhost:{candidate}"}
        try:
            return Server(("127.0.0.1", candidate), handler)
        except OSError as exc:
            last = exc
    raise OSError(f"no free port from {port} to {port + tries - 1}: {last}")
