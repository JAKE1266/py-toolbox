"""文本统计。

支持中英混排:英文按单词计数,中文按字计数,合并为总「词数」。
"""

from __future__ import annotations

import re
from pathlib import Path

#: CJK 统一表意文字(含扩展 A 与兼容区)
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
#: 英文/数字单词(允许内部连字符与撇号)
_LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*")


def text_stats(text: str) -> dict:
    """统计文本,返回字符数、词数、行数、UTF-8 字节数等信息。"""
    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")

    cjk = len(_CJK_RE.findall(text))
    latin_words = _LATIN_WORD_RE.findall(text)
    no_space = re.sub(r"\s", "", text)

    return {
        "chars": len(text),
        "chars_no_space": len(no_space),
        "cjk_chars": cjk,
        "latin_words": len(latin_words),
        "words": len(latin_words) + cjk,
        "lines": len(text.splitlines()) if text.strip() else 0,
        "bytes_utf8": len(text.encode("utf-8")),
    }


def stats_from_file(path, encoding: str = "utf-8") -> dict:
    """读取文本文件并统计,额外带上 ``file`` 字段。"""
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"文件不存在:{file}")
    stats = text_stats(file.read_text(encoding=encoding, errors="replace"))
    stats["file"] = str(file)
    return stats
