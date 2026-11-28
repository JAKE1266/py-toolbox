"""命令行入口测试:直接调用 ``main()``,捕获 stdout 校验 JSON 输出。"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

import pytoolbox
from pytoolbox.cli import main


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_version(self):
        stdout, _ = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("pytoolbox", stdout.getvalue())

    def test_no_args_shows_help(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("usage", out.lower())

    def test_passgen_json(self):
        code, out, _ = self.run_cli("passgen", "--count", "2", "--length", "12", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(len(data["passwords"]), 2)
        for item in data["passwords"]:
            self.assertEqual(len(item["password"]), 12)
            self.assertIn("score", item)

    def test_organize_dry_run(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "x.png").write_bytes(b"")
            code, out, _ = self.run_cli("organize", folder, "--dry-run", "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["total"], 1)
            self.assertTrue(Path(folder, "x.png").is_file())  # dry-run 未移动

    def test_organize_invalid_folder(self):
        code, _, err = self.run_cli("organize", "Z:/no/such/dir", "--json")
        self.assertEqual(code, 1)
        self.assertIn("错误", err)

    def test_stats_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "note.txt")
            path.write_text("你好世界 hello", encoding="utf-8")
            code, out, _ = self.run_cli("stats", str(path), "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["cjk_chars"], 4)
            self.assertEqual(data["latin_words"], 1)

    def test_utf8_under_legacy_console_encoding(self):
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        env.pop("PYTHONPATH", None)
        try:
            installed = distribution("pytoolbox")
            installed_init = Path(installed.locate_file("pytoolbox/__init__.py"))
            if installed.version != pytoolbox.__version__ or not installed_init.is_file():
                raise PackageNotFoundError
        except PackageNotFoundError:
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [sys.executable, "-m", "pytoolbox", "--help"],
            capture_output=True, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        self.assertIn("密码", result.stdout.decode("utf-8"))

        result = subprocess.run(
            [sys.executable, "-m", "pytoolbox", "stats", "--json"],
            input="你好 world".encode("utf-8"),
            capture_output=True, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        data = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(data["cjk_chars"], 2)
        self.assertEqual(data["latin_words"], 1)

    def test_human_output(self):
        code, out, _ = self.run_cli("passgen", "--count", "1")
        self.assertEqual(code, 0)
        self.assertIn("(" , out)  # 含强度说明


if __name__ == "__main__":
    unittest.main()
