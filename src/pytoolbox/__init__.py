"""PyToolBox —— 一个仓库,四种用法:Python 库 / 命令行 / 网页版 / 桌面 GUI。

所有功能仅依赖 Python 标准库,无需安装任何第三方包。

快速上手::

    from pytoolbox import organize, batch_rename, find_duplicates, generate_password, text_stats

    organize("C:/Users/you/Downloads")        # 按类型整理文件夹
    generate_password(20)                     # 生成强密码
"""

from pytoolbox.core.dedupe import find_duplicates, hash_file
from pytoolbox.core.organizer import classify, organize
from pytoolbox.core.passgen import estimate_strength, generate_password, generate_passwords
from pytoolbox.core.renamer import batch_rename
from pytoolbox.core.textstats import stats_from_file, text_stats

__version__ = "1.0.1"

__all__ = [
    "batch_rename",
    "classify",
    "estimate_strength",
    "find_duplicates",
    "generate_password",
    "generate_passwords",
    "hash_file",
    "organize",
    "stats_from_file",
    "text_stats",
    "__version__",
]
