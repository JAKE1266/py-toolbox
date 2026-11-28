"""PyToolBox 网页版:仅用标准库 :mod:`http.server` 实现的本地 Web 界面。

默认只监听 127.0.0.1(本机回环地址),不会暴露到局域网;
如需局域网访问,请显式传 ``--host 0.0.0.0`` 并自行承担网络安全责任。
"""

from __future__ import annotations

import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .core.dedupe import find_duplicates
from .core.organizer import organize
from .core.passgen import estimate_strength, generate_passwords
from .core.renamer import batch_rename
from .core.textstats import text_stats

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_ERROR_TYPES = (KeyError, TypeError, ValueError, OSError, NotADirectoryError, FileNotFoundError, RuntimeError)
_SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'none'"
    ),
}


# ---------------------------------------------------------------- API 处理函数

def _api_organize(payload: dict) -> dict:
    return organize(payload["folder"], dry_run=bool(payload.get("dry_run")))


def _api_rename(payload: dict) -> dict:
    return batch_rename(
        payload["folder"],
        dry_run=bool(payload.get("dry_run")),
        prefix=str(payload.get("prefix", "file_")),
        suffix=str(payload.get("suffix", "")),
        start=int(payload.get("start", 1)),
        padding=int(payload.get("padding", 3)),
    )


def _api_dedupe(payload: dict) -> dict:
    return find_duplicates(payload["folder"], recursive=bool(payload.get("recursive")))


def _api_passgen(payload: dict) -> dict:
    passwords = generate_passwords(
        int(payload.get("count", 5)),
        length=int(payload.get("length", 16)),
        upper=bool(payload.get("upper", True)),
        lower=bool(payload.get("lower", True)),
        digits=bool(payload.get("digits", True)),
        symbols=bool(payload.get("symbols", True)),
        exclude_ambiguous=bool(payload.get("exclude_ambiguous", True)),
    )
    return {"passwords": [dict(password=pw, **estimate_strength(pw)) for pw in passwords]}


def _api_stats(payload: dict) -> dict:
    return text_stats(str(payload.get("text", "")))


def _api_listdir(payload: dict) -> dict:
    folder = Path(payload["folder"])
    if not folder.is_dir():
        raise NotADirectoryError(f"目录不存在或不是文件夹:{folder}")
    dirs, files = [], []
    for entry in sorted(folder.iterdir(), key=lambda p: p.name):
        (dirs if entry.is_dir() else files).append(entry.name)
    return {"folder": str(folder), "dirs": dirs, "files": files}


ROUTES = {
    "/api/organize": _api_organize,
    "/api/rename": _api_rename,
    "/api/dedupe": _api_dedupe,
    "/api/passgen": _api_passgen,
    "/api/stats": _api_stats,
    "/api/listdir": _api_listdir,
}


# ---------------------------------------------------------------- HTTP 服务

class _Handler(BaseHTTPRequestHandler):
    server_version = f"PyToolBox/{__version__}"

    # ---------------------------------------------------------------- 安全层

    def _security_headers(self) -> None:
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)

    def _host_allowed(self) -> bool:
        supplied = self.headers.get("Host", "").lower()
        return bool(supplied) and supplied in getattr(self.server, "allowed_hosts", set())

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        host = self.headers.get("Host", "")
        return origin.lower().rstrip("/") == f"http://{host}".lower()

    def _authorized(self) -> bool:
        expected = getattr(self.server, "auth_token", "")
        provided = self.headers.get("X-PyToolBox-Token", "")
        return bool(expected and provided) and secrets.compare_digest(
            provided.encode("utf-8"), expected.encode("utf-8")
        )

    # ---------------------------------------------------------------- 响应

    def _send(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, obj: dict) -> None:
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _reject_json(self, code: int, obj: dict) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if 0 < length <= 1024 * 1024:
            self.rfile.read(length)
        self.close_connection = True
        self._send_json(code, obj)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8",
                       (TEMPLATES_DIR / "index.html").read_bytes())
        elif self.path == "/api/health":
            self._send_json(200, {"ok": True, "version": __version__})
        else:
            self._send(404, "text/plain; charset=utf-8", "404 Not Found".encode("utf-8"))

    def do_POST(self) -> None:
        handler = ROUTES.get(self.path.split("?")[0])
        if handler is None:
            self._send_json(404, {"ok": False, "error": "未知接口"})
            return
        if not self._host_allowed():
            self._reject_json(403, {"ok": False, "error": "不受信任的 Host"})
            return
        if not self._same_origin():
            self._reject_json(403, {"ok": False, "error": "跨源请求已拒绝"})
            return
        if not self._authorized():
            self._reject_json(401, {"ok": False, "error": "缺少或错误的访问令牌"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            self._send_json(400, {"ok": False, "error": f"请求体不是合法 JSON:{exc}"})
            return
        try:
            self._send_json(200, {"ok": True, "data": handler(payload)})
        except KeyError as exc:
            self._send_json(400, {"ok": False, "error": f"缺少参数:{exc.args[0]}"})
        except _ERROR_TYPES as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args) -> None:  # 精简日志,避免刷屏
        print(f"[web] {fmt % args}")


def _create_server(host: str = "127.0.0.1", port: int = 8000, token: str | None = None):
    server = ThreadingHTTPServer((host, port), _Handler)
    actual_port = server.server_address[1]
    hostnames = {host, server.server_address[0]}
    if host in ("", "0.0.0.0", "127.0.0.1", "localhost"):
        hostnames.update(("127.0.0.1", "localhost"))
    server.allowed_hosts = {f"{name}:{actual_port}".lower() for name in hostnames}
    server.auth_token = token or secrets.token_urlsafe(32)
    return server


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    """启动网页版服务(阻塞运行,Ctrl+C 停止)。"""
    server = _create_server(host, port)
    display_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    url = f"http://{display_host}:{server.server_address[1]}/#token={server.auth_token}"
    print(f"PyToolBox 网页版 v{__version__}")
    print(f"地址:{url}(监听 {host},{'仅本机可访问' if host == '127.0.0.1' else '已对局域网开放,注意安全'})")
    print("请使用打印的完整地址访问;URL 片段中的令牌不会发送给服务器,页面会自动携带它调用 API。")
    print("按 Ctrl+C 停止服务。")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()
