"""核心功能层单元测试(仅用标准库 unittest 运行)。"""

import tempfile
import unittest
from pathlib import Path

from pytoolbox.core.dedupe import find_duplicates, hash_file
from pytoolbox.core.organizer import classify, organize
from pytoolbox.core.passgen import estimate_strength, generate_password, generate_passwords
from pytoolbox.core.renamer import batch_rename
from pytoolbox.core.textstats import text_stats


class TempDirTestCase(unittest.TestCase):
    """为每个测试准备独立的临时目录。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def touch(self, name: str, content: bytes = b"hello") -> Path:
        path = self.dir / name
        path.write_bytes(content)
        return path


class OrganizerTest(TempDirTestCase):
    def test_classify(self):
        self.assertEqual(classify("a.jpg"), "图片")
        self.assertEqual(classify("b.PDF"), "文档")
        self.assertEqual(classify("clip.mp4"), "视频")
        self.assertEqual(classify("c.unknownext"), "其他")

    def test_organize_moves_by_category(self):
        self.touch("photo.jpg")
        self.touch("doc.pdf")
        self.touch("song.mp3")
        result = organize(self.dir)
        self.assertEqual(result["total"], 3)
        self.assertTrue((self.dir / "图片" / "photo.jpg").is_file())
        self.assertTrue((self.dir / "文档" / "doc.pdf").is_file())
        self.assertTrue((self.dir / "音频" / "song.mp3").is_file())

    def test_dry_run_does_not_move(self):
        path = self.touch("a.png")
        result = organize(self.dir, dry_run=True)
        self.assertEqual(result["total"], 1)
        self.assertTrue(path.is_file())
        self.assertFalse((self.dir / "图片").exists())

    def test_name_collision_resolved(self):
        (self.dir / "图片").mkdir()
        (self.dir / "图片" / "a.jpg").write_bytes(b"old")
        self.touch("a.jpg")
        result = organize(self.dir)
        self.assertEqual(result["total"], 1)
        self.assertTrue((self.dir / "图片" / "a (1).jpg").is_file())

    def test_invalid_folder(self):
        with self.assertRaises(NotADirectoryError):
            organize(self.dir / "不存在的目录")


class RenamerTest(TempDirTestCase):
    def test_rename_numbering(self):
        for name in ("a.txt", "b.txt", "c.txt"):
            self.touch(name)
        result = batch_rename(self.dir, prefix="file_")
        self.assertEqual(result["total"], 3)
        names = sorted(p.name for p in self.dir.iterdir())
        self.assertEqual(names, ["file_001.txt", "file_002.txt", "file_003.txt"])

    def test_dry_run(self):
        self.touch("a.txt")
        batch_rename(self.dir, dry_run=True)
        self.assertTrue((self.dir / "a.txt").is_file())

    def test_extension_case_preserved(self):
        self.touch("IMG.JPG")
        batch_rename(self.dir, prefix="pic_")
        self.assertIn("pic_001.JPG", [p.name for p in self.dir.iterdir()])

    def test_no_op_when_already_numbered(self):
        self.touch("file_001.txt")
        result = batch_rename(self.dir, prefix="file_")
        self.assertEqual(result["total"], 0)
        self.assertTrue((self.dir / "file_001.txt").is_file())

    def test_existing_target_avoided(self):
        self.touch("file_001.txt")
        self.touch("a.txt")
        result = batch_rename(self.dir, prefix="file_")
        renamed = {c["to"] for c in result["changes"]}
        self.assertNotIn("file_001.txt", renamed)  # 不允许覆盖已存在的序号


class DedupeTest(TempDirTestCase):
    def test_find_duplicates(self):
        self.touch("dup1.txt", b"hello world")
        self.touch("dup2.txt", b"hello world")
        self.touch("unique.txt", b"other content")
        result = find_duplicates(self.dir)
        self.assertEqual(result["group_count"], 1)
        (paths,) = result["groups"].values()
        self.assertEqual(len(paths), 2)
        self.assertEqual(result["wasted_bytes"], len(b"hello world"))

    def test_no_duplicates(self):
        self.touch("a.txt", b"1")
        self.touch("b.txt", b"2")
        self.assertEqual(find_duplicates(self.dir)["group_count"], 0)

    def test_recursive(self):
        self.touch("a.txt", b"same")
        sub = self.dir / "sub"
        sub.mkdir()
        (sub / "b.txt").write_bytes(b"same")
        top_only = find_duplicates(self.dir)
        self.assertEqual(top_only["group_count"], 0)
        deep = find_duplicates(self.dir, recursive=True)
        self.assertEqual(deep["group_count"], 1)

    def test_hash_file(self):
        path = self.touch("f.txt", b"abc")
        self.assertEqual(hash_file(path), "900150983cd24fb0d6963f7d28e17f72")


class PassgenTest(unittest.TestCase):
    def test_length_and_charset(self):
        pw = generate_password(24)
        self.assertEqual(len(pw), 24)
        self.assertTrue(any(c.isdigit() for c in pw))
        self.assertTrue(any(c.islower() for c in pw))
        self.assertTrue(any(c.isupper() for c in pw))
        self.assertTrue(any(c in "!@#$%^&*()-_=+[]{};:,.<>?" for c in pw))

    def test_exclude_ambiguous(self):
        pw = generate_password(64)
        self.assertFalse(any(c in "Il1O0o" for c in pw))

    def test_no_symbols(self):
        pw = generate_password(20, symbols=False)
        self.assertFalse(any(c in "!@#$%^&*()-_=+[]{};:,.<>?" for c in pw))

    def test_invalid_length(self):
        with self.assertRaises(ValueError):
            generate_password(2)
        with self.assertRaises(ValueError):
            generate_password(8, upper=False, lower=False, digits=False, symbols=False)

    def test_batch(self):
        passwords = generate_passwords(10, length=16)
        self.assertEqual(len(passwords), 10)
        self.assertEqual(len(set(passwords)), 10)  # 随机性足够,不重复

    def test_strength(self):
        weak = estimate_strength("1111")
        self.assertEqual(weak["score"], 0)
        strong = estimate_strength("Xk9$mP2#vLq8")
        self.assertGreaterEqual(strong["entropy_bits"], 60)


class TextStatsTest(unittest.TestCase):
    def test_mixed_text(self):
        text = "Hello 世界!\n第二行 world"
        stats = text_stats(text)
        self.assertEqual(stats["chars"], 19)
        self.assertEqual(stats["lines"], 2)
        self.assertEqual(stats["cjk_chars"], 5)
        self.assertEqual(stats["latin_words"], 2)
        self.assertEqual(stats["words"], 7)

    def test_empty(self):
        stats = text_stats("")
        self.assertEqual(stats["chars"], 0)
        self.assertEqual(stats["lines"], 0)
        self.assertEqual(stats["words"], 0)

    def test_type_check(self):
        with self.assertRaises(TypeError):
            text_stats(123)


if __name__ == "__main__":
    unittest.main()
