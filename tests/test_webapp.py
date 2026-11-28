"""网页版访问控制端到端测试。"""

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from pytoolbox.webapp import _create_server


class WebAppSecurityTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name) / "files"
        self.folder.mkdir()
        self.source = self.folder / "photo.png"
        self.source.write_bytes(b"image")
        self.server = _create_server("127.0.0.1", 0, token="test-token")
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join, 2)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, payload=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = dict(headers or {})
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            data = response.read()
            if response.getheader("Content-Type", "").startswith("application/json"):
                data = json.loads(data.decode("utf-8"))
            return response.status, dict(response.getheaders()), data
        finally:
            connection.close()

    def organize(self, headers):
        return self.request(
            "POST", "/api/organize", {"folder": str(self.folder), "dry_run": False},
            headers,
        )

    def test_missing_token_is_rejected_without_moving_files(self):
        status, _, body = self.organize({})
        self.assertEqual(status, 401)
        self.assertFalse(body["ok"])
        self.assertTrue(self.source.is_file())

    def test_wrong_token_is_rejected_without_moving_files(self):
        status, _, _ = self.organize({"X-PyToolBox-Token": "wrong"})
        self.assertEqual(status, 401)
        self.assertTrue(self.source.is_file())

    def test_cross_origin_request_is_rejected_even_with_token(self):
        status, _, body = self.organize({
            "X-PyToolBox-Token": "test-token",
            "Origin": "https://evil.example",
        })
        self.assertEqual(status, 403)
        self.assertFalse(body["ok"])
        self.assertTrue(self.source.is_file())

    def test_foreign_host_is_rejected_even_with_token(self):
        status, _, body = self.organize({
            "X-PyToolBox-Token": "test-token",
            "Host": "evil.example",
            "Origin": "http://evil.example",
        })
        self.assertEqual(status, 403)
        self.assertFalse(body["ok"])
        self.assertTrue(self.source.is_file())

    def test_same_origin_request_with_token_can_organize(self):
        status, _, body = self.organize({
            "X-PyToolBox-Token": "test-token",
            "Origin": f"http://127.0.0.1:{self.port}",
        })
        self.assertEqual(status, 200, body)
        self.assertTrue(body["ok"])
        self.assertFalse(self.source.exists())
        self.assertTrue((self.folder / "图片" / "photo.png").is_file())

    def test_health_and_index_remain_available_without_token(self):
        status, _, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, headers, page = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn(b"X-PyToolBox-Token", page)
        self.assertIn(b"location.hash", page)
        self.assertNotIn(b"test-token", page)


if __name__ == "__main__":
    unittest.main()
