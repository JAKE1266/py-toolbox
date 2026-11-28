import http.client
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
import threading
from importlib.metadata import distribution
from pathlib import Path

import pytoolbox
from pytoolbox.webapp import _create_server


dist = distribution("pytoolbox")
assert dist.version == pytoolbox.__version__ == "1.0.1"
assert dist.metadata["Requires-Python"] == ">=3.9"
assert not dist.requires
assert dist.read_text("top_level.txt").split() == ["pytoolbox"]
assert Path(pytoolbox.__file__).resolve() == Path(
    dist.locate_file("pytoolbox/__init__.py")).resolve()
assert any(
    ep.group == "console_scripts"
    and ep.name == "pytoolbox"
    and ep.value == "pytoolbox.cli:main"
    for ep in dist.entry_points
)
assert len(pytoolbox.generate_password(20)) == 20
template = Path(pytoolbox.__file__).resolve().parent / "templates" / "index.html"
assert template.is_file()
page = template.read_text(encoding="utf-8")
assert "location.hash" in page
assert "X-PyToolBox-Token" in page
assert "innerHTML" not in page

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    folder = root / "文件"
    folder.mkdir()
    source = folder / "photo.png"
    source.write_bytes(b"image")
    server = _create_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, payload=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = dict(headers or {})
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), data
        finally:
            connection.close()

    try:
        status, _, _ = request(
            "POST", "/api/organize", {"folder": str(folder), "dry_run": False})
        assert status == 401
        assert source.is_file()

        status, headers, body = request(
            "POST", "/api/organize", {"folder": str(folder), "dry_run": False},
            {"X-PyToolBox-Token": server.auth_token,
             "Origin": f"http://127.0.0.1:{port}"})
        assert status == 200, body
        assert not source.exists()
        assert (folder / "图片" / "photo.png").is_file()
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]

        status, _, body = request("GET", "/")
        assert status == 200
        assert server.auth_token.encode("ascii") not in body
    finally:
        server.shutdown()
        thread.join(2)
        server.server_close()

    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytoolbox", "--help"],
        cwd=tmp, capture_output=True, env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert "密码" in result.stdout.decode("utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "pytoolbox", "stats", "--json"],
        input="你好 world".encode("utf-8"),
        cwd=tmp, capture_output=True, env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    data = json.loads(result.stdout.decode("utf-8"))
    assert data["cjk_chars"] == 2
    assert data["latin_words"] == 1

    result = subprocess.run(
        [sys.executable, "-m", "pytoolbox", "--version"],
        cwd=tmp, capture_output=True, env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert "pytoolbox 1.0.1" in result.stdout.decode("utf-8")

    script = Path(sysconfig.get_path("scripts")) / (
        "pytoolbox.exe" if os.name == "nt" else "pytoolbox")
    assert script.is_file(), script
    result = subprocess.run(
        [str(script), "passgen", "--count", "1", "--json"],
        cwd=tmp, capture_output=True, env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert len(json.loads(result.stdout.decode("utf-8"))["passwords"]) == 1

print("installed smoke: OK")
