"""按文件类型整理文件夹。

把散落在目录里的文件按扩展名归入「图片 / 文档 / 音频 / 视频 / 压缩包 / 代码 / 其他」
等分类子目录,支持 dry-run 预览。
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

#: 扩展名 -> 分类名
CATEGORY_MAP: dict = {}
for _cat, _exts in {
    "图片": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tif", ".tiff"},
    "文档": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
            ".md", ".markdown", ".csv", ".rtf", ".odt", ".epub"},
    "音频": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "视频": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "压缩包": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "代码": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".java", ".c", ".h",
            ".cpp", ".go", ".rs", ".php", ".rb", ".sh", ".bat", ".ps1", ".sql",
            ".json", ".xml", ".yaml", ".yml", ".toml", ".ini"},
}.items():
    for _ext in _exts:
        CATEGORY_MAP[_ext] = _cat

OTHER = "其他"


def classify(filename: str) -> str:
    """根据扩展名返回分类名,未识别的类型归入「其他」。"""
    return CATEGORY_MAP.get(Path(filename).suffix.lower(), OTHER)


@dataclass
class MoveAction:
    """一次待执行的移动计划。"""

    src: Path
    dst: Path
    category: str


def unique_path(dst: Path) -> Path:
    """若目标路径已存在,返回追加「 (1)」「 (2)」…的新路径。"""
    if not dst.exists():
        return dst
    stem, suffix, parent = dst.stem, dst.suffix, dst.parent
    for i in range(1, 1000):
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法为 {dst} 生成不重名的目标路径")


def plan_organize(folder, include_hidden: bool = False) -> list:
    """生成整理计划(不执行任何移动),返回 :class:`MoveAction` 列表。"""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"目录不存在或不是文件夹:{folder}")

    planned = []
    for entry in sorted(folder.iterdir(), key=lambda p: p.name):
        if not include_hidden and entry.name.startswith("."):
            continue
        if not entry.is_file():
            continue  # 跳过子目录(包括分类目录本身)
        category = classify(entry.name)
        dst = unique_path(folder / category / entry.name)
        planned.append(MoveAction(entry, dst, category))
    return planned


def organize(folder, dry_run: bool = False) -> dict:
    """按类型整理 ``folder`` 下的文件。

    :param folder: 目标文件夹
    :param dry_run: 为 True 时只返回计划,不实际移动文件
    :returns: 包含 ``total`` / ``summary`` / ``details`` 的字典
    """
    folder = Path(folder)
    planned = plan_organize(folder)

    details: dict = {}
    for action in planned:
        details.setdefault(action.category, []).append({
            "from": action.src.name,
            "to": action.dst.relative_to(folder).as_posix(),
        })

    if not dry_run:
        for action in planned:
            action.dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(action.src), str(action.dst))

    return {
        "folder": str(folder),
        "total": len(planned),
        "dry_run": dry_run,
        "summary": {cat: len(items) for cat, items in details.items()},
        "details": details,
    }
