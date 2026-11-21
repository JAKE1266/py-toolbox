"""批量重命名。

把目录下的文件统一重命名为 ``前缀 + 序号 + 后缀 + 扩展名`` 的形式,
例如 ``photo_001.jpg``。自动跳过同名文件、自动解决命名冲突。
"""

from __future__ import annotations

from pathlib import Path


def plan_rename(folder, prefix: str = "file_", suffix: str = "",
                start: int = 1, padding: int = 3,
                include_hidden: bool = False) -> list:
    """生成重命名计划(不执行),返回 ``(旧路径, 新路径)`` 元组列表。"""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"目录不存在或不是文件夹:{folder}")
    if start < 0 or padding < 1:
        raise ValueError("start 不能为负,padding 至少为 1")

    actions = []
    counter = start
    taken = set()
    for entry in sorted(folder.iterdir(), key=lambda p: p.name):
        if not include_hidden and entry.name.startswith("."):
            continue
        if not entry.is_file():
            continue
        # 找到一个未被占用且不与现有文件冲突的序号
        while True:
            candidate = f"{prefix}{counter:0{padding}d}{suffix}{entry.suffix}"
            if candidate == entry.name or (candidate not in taken and not (folder / candidate).exists()):
                break
            counter += 1
        taken.add(candidate)
        counter += 1
        if candidate != entry.name:
            actions.append((entry, folder / candidate))
    return actions


def batch_rename(folder, dry_run: bool = False, prefix: str = "file_",
                 suffix: str = "", start: int = 1, padding: int = 3) -> dict:
    """批量重命名 ``folder`` 下的文件(仅顶层文件)。

    :param dry_run: 为 True 时只返回计划,不实际重命名
    :returns: 包含 ``total`` 与 ``changes`` 的字典
    """
    folder = Path(folder)
    planned = plan_rename(folder, prefix=prefix, suffix=suffix,
                          start=start, padding=padding)
    if not dry_run:
        for src, dst in planned:
            src.rename(dst)
    return {
        "folder": str(folder),
        "total": len(planned),
        "dry_run": dry_run,
        "changes": [{"from": src.name, "to": dst.name} for src, dst in planned],
    }
