"""查找重复文件。

先用文件大小粗筛,再对同大小的文件计算哈希精确比对,避免为所有文件算哈希。
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

_CHUNK_SIZE = 64 * 1024

#: 允许使用的哈希算法
SUPPORTED_ALGOS = ("md5", "sha1", "sha256")


def hash_file(path, algo: str = "md5") -> str:
    """计算文件哈希值,大文件分块读取,内存占用恒定。"""
    if algo not in SUPPORTED_ALGOS:
        raise ValueError(f"不支持的算法 {algo!r},可选:{', '.join(SUPPORTED_ALGOS)}")
    digest = hashlib.new(algo)
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(folder: Path, recursive: bool):
    if recursive:
        for path in folder.rglob("*"):
            if path.is_file():
                yield path
    else:
        for path in folder.iterdir():
            if path.is_file():
                yield path


def find_duplicates(folder, recursive: bool = False, algo: str = "md5") -> dict:
    """查找 ``folder`` 中内容完全相同的文件。

    :param recursive: 是否递归子目录
    :param algo: 哈希算法,可选 ``md5`` / ``sha1`` / ``sha256``
    :returns: 包含 ``groups``(哈希 -> 路径列表,只含重复组)、
        ``wasted_bytes``(可释放空间)等字段的字典
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"目录不存在或不是文件夹:{folder}")

    # 第一阶段:按文件大小分组,大小唯一的文件不可能重复
    by_size = defaultdict(list)
    for path in _iter_files(folder, recursive):
        try:
            by_size[path.stat().st_size].append(path)
        except OSError:
            continue
    candidates = [paths for paths in by_size.values() if len(paths) > 1]

    # 第二阶段:对同大小的文件计算哈希精确比对
    groups = defaultdict(list)
    for paths in candidates:
        for path in paths:
            try:
                groups[hash_file(path, algo)].append(path)
            except OSError:
                continue

    duplicates = {
        digest: sorted(paths, key=str)
        for digest, paths in groups.items()
        if len(paths) > 1
    }
    wasted = 0
    for paths in duplicates.values():
        try:
            wasted += paths[0].stat().st_size * (len(paths) - 1)
        except OSError:
            continue

    return {
        "folder": str(folder),
        "recursive": recursive,
        "algo": algo,
        "group_count": len(duplicates),
        "groups": {digest: [str(p) for p in paths] for digest, paths in duplicates.items()},
        "wasted_bytes": wasted,
    }
