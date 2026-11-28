"""PyToolBox 命令行入口。

运行 ``pytoolbox --help`` 或 ``python -m pytoolbox --help`` 查看全部子命令。
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core.dedupe import find_duplicates
from .core.organizer import organize
from .core.passgen import estimate_strength, generate_passwords
from .core.renamer import batch_rename
from .core.textstats import stats_from_file, text_stats


def _format_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _configure_standard_streams() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- 子命令实现

def cmd_organize(args) -> int:
    result = organize(args.folder, dry_run=args.dry_run)
    if args.json:
        _print_json(result)
        return 0

    print(f"目录:{result['folder']}")
    if result["total"] == 0:
        print("没有需要整理的文件。")
        return 0
    print(f"共 {result['total']} 个文件{'(预览)' if result['dry_run'] else ''}")
    for category, items in result["details"].items():
        print(f"\n[{category}] {len(items)} 个")
        for item in items:
            print(f"  {item['from']}  ->  {item['to']}")
    if result["dry_run"]:
        print("\n※ dry-run 预览模式,未实际移动文件;去掉 --dry-run 后执行。")
    else:
        print(f"\n[OK] 已移动 {result['total']} 个文件。")
    return 0


def cmd_rename(args) -> int:
    result = batch_rename(args.folder, dry_run=args.dry_run, prefix=args.prefix,
                          suffix=args.suffix, start=args.start, padding=args.padding)
    if args.json:
        _print_json(result)
        return 0

    print(f"目录:{result['folder']}")
    if result["total"] == 0:
        print("没有需要重命名的文件。")
        return 0
    for change in result["changes"]:
        print(f"  {change['from']}  ->  {change['to']}")
    if result["dry_run"]:
        print(f"\n※ dry-run 预览:将重命名 {result['total']} 个文件(未执行)。")
    else:
        print(f"\n[OK] 已重命名 {result['total']} 个文件。")
    return 0


def cmd_dedupe(args) -> int:
    result = find_duplicates(args.folder, recursive=args.recursive, algo=args.algo)
    if args.json:
        _print_json(result)
        return 0

    if result["group_count"] == 0:
        print("未发现重复文件。")
        return 0
    print(f"发现 {result['group_count']} 组重复文件,可释放 {_format_bytes(result['wasted_bytes'])}")
    for digest, paths in result["groups"].items():
        print(f"\n[{digest[:12]}] {len(paths)} 个相同文件:")
        for i, path in enumerate(paths):
            mark = "[保留]" if i == 0 else "[重复]"
            print(f"  {mark} {path}")
    print("\n※ 保留每组第一个文件,其余可自行确认后手动删除。")
    return 0


def cmd_passgen(args) -> int:
    passwords = generate_passwords(
        args.count,
        length=args.length,
        upper=not args.no_upper,
        lower=not args.no_lower,
        digits=not args.no_digits,
        symbols=not args.no_symbols,
        exclude_ambiguous=not args.allow_ambiguous,
    )
    if args.json:
        _print_json({"passwords": [dict(password=pw, **estimate_strength(pw)) for pw in passwords]})
        return 0

    for pw in passwords:
        strength = estimate_strength(pw)
        print(f"  {pw}   ({strength['label']}, {strength['entropy_bits']} bits)")
    return 0


def cmd_stats(args) -> int:
    if args.input:
        result = stats_from_file(args.input, encoding=args.encoding)
    else:
        result = text_stats(sys.stdin.read())
    if args.json:
        _print_json(result)
        return 0

    label = result.get("file", "(标准输入)")
    print(f"文本统计:{label}")
    print(f"  总字符数     {result['chars']}")
    print(f"  字符(去空白) {result['chars_no_space']}")
    print(f"  中文字符     {result['cjk_chars']}")
    print(f"  英文单词     {result['latin_words']}")
    print(f"  总词数       {result['words']}")
    print(f"  行数         {result['lines']}")
    print(f"  UTF-8 字节   {result['bytes_utf8']}")
    return 0


def cmd_web(args) -> int:
    from .webapp import serve

    serve(args.host, args.port, open_browser=not args.no_browser)
    return 0


def cmd_gui(args) -> int:
    from .gui import run

    run()
    return 0


# ---------------------------------------------------------------- 参数解析

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytoolbox",
        description="PyToolBox —— 零依赖的多功能工具箱:文件整理 / 批量重命名 / 重复文件 / 密码 / 文本统计",
    )
    parser.add_argument("--version", action="version", version=f"pytoolbox {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("organize", help="按类型整理文件夹(图片/文档/视频…)")
    p.add_argument("folder", help="目标文件夹")
    p.add_argument("-n", "--dry-run", action="store_true", help="仅预览,不实际移动")
    p.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p.set_defaults(func=cmd_organize)

    p = sub.add_parser("rename", help="批量重命名(前缀+序号)")
    p.add_argument("folder", help="目标文件夹")
    p.add_argument("-p", "--prefix", default="file_", help="文件名前缀(默认 file_)")
    p.add_argument("-s", "--suffix", default="", help="序号后的后缀")
    p.add_argument("--start", type=int, default=1, help="起始序号(默认 1)")
    p.add_argument("--padding", type=int, default=3, help="序号补零位数(默认 3)")
    p.add_argument("-n", "--dry-run", action="store_true", help="仅预览,不实际重命名")
    p.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("dedupe", help="按内容查找重复文件")
    p.add_argument("folder", help="目标文件夹")
    p.add_argument("-r", "--recursive", action="store_true", help="递归子目录")
    p.add_argument("--algo", choices=("md5", "sha1", "sha256"), default="md5", help="哈希算法")
    p.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p.set_defaults(func=cmd_dedupe)

    p = sub.add_parser("passgen", help="生成强密码")
    p.add_argument("-l", "--length", type=int, default=16, help="密码长度(默认 16)")
    p.add_argument("-c", "--count", type=int, default=5, help="生成数量(默认 5)")
    p.add_argument("--no-upper", action="store_true", help="不含大写字母")
    p.add_argument("--no-lower", action="store_true", help="不含小写字母")
    p.add_argument("--no-digits", action="store_true", help="不含数字")
    p.add_argument("--no-symbols", action="store_true", help="不含特殊符号")
    p.add_argument("--allow-ambiguous", action="store_true", help="允许 Il1O0o 等易混淆字符")
    p.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p.set_defaults(func=cmd_passgen)

    p = sub.add_parser("stats", help="文本统计(传文件路径,或用管道传入文本)")
    p.add_argument("input", nargs="?", default=None, help="文本文件路径;省略则读标准输入")
    p.add_argument("--encoding", default="utf-8", help="文件编码(默认 utf-8)")
    p.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("web", help="启动本地网页版")
    p.add_argument("--host", default="127.0.0.1", help="监听地址(默认仅本机)")
    p.add_argument("--port", type=int, default=8000, help="端口(默认 8000)")
    p.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    p.set_defaults(func=cmd_web)

    p = sub.add_parser("gui", help="启动桌面 GUI(需要 Tkinter)")
    p.set_defaults(func=cmd_gui)

    return parser


def main(argv=None) -> int:
    _configure_standard_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except BrokenPipeError:
        return 0
    except (NotADirectoryError, FileNotFoundError, ValueError, TypeError, RuntimeError, OSError) as exc:
        print(f"错误:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
