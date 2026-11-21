"""PyToolBox 桌面版:标准库 Tkinter 实现的图形界面。

运行 ``python -m pytoolbox gui`` 启动。文件操作放在后台线程执行,避免卡住界面。
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import __version__
from .core.dedupe import find_duplicates
from .core.organizer import organize
from .core.passgen import estimate_strength, generate_passwords
from .core.renamer import batch_rename
from .core.textstats import text_stats


def _format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class ToolBoxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"PyToolBox 工具箱 v{__version__}")
        self.geometry("840x600")
        self.minsize(720, 500)

        self.output = None  # 底部共享输出区
        self._build()

    # ------------------------------------------------------------- 界面搭建

    def _build(self):
        style = ttk.Style(self)
        for theme in ("vista", "clam"):
            try:
                style.theme_use(theme)
                break
            except tk.TclError:
                continue

        header = tk.Label(self, text="PyToolBox 工具箱", font=("TkDefaultFont", 16, "bold"),
                          anchor="w", padx=12, pady=8)
        header.pack(fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        notebook.add(self._tab_organize(notebook), text=" 文件整理 ")
        notebook.add(self._tab_rename(notebook), text=" 批量重命名 ")
        notebook.add(self._tab_dedupe(notebook), text=" 重复文件 ")
        notebook.add(self._tab_passgen(notebook), text=" 密码生成 ")
        notebook.add(self._tab_stats(notebook), text=" 文本统计 ")

        box = tk.LabelFrame(self, text=" 输出 ", padx=6, pady=6)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.output = scrolledtext.ScrolledText(box, height=10, state="disabled",
                                                wrap="word", font=("TkFixedFont", 10))
        self.output.pack(fill="both", expand=True)

    def _path_row(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=4)
        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(side="left", fill="x", expand=True)

        def browse():
            chosen = filedialog.askdirectory(parent=self)
            if chosen:
                var.set(chosen)

        ttk.Button(frame, text="浏览…", command=browse).pack(side="left", padx=(6, 0))
        return var

    @staticmethod
    def _row(parent) -> ttk.Frame:
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=4)
        return frame

    def _run_button(self, parent, fn, before=None):
        """创建执行按钮;任务在后台线程运行,完成后写回输出区。

        :param before: 可选回调,在【主线程】点击时先执行,用于安全地读取界面控件。
        """
        def worker(arg):
            try:
                text, error = fn(arg), None
            except Exception as exc:  # 后台线程:捕获后回到主线程提示
                text, error = None, exc
            self.after(0, lambda: self._finish(btn, text, error))

        def start():
            btn.config(state="disabled")
            self._log(f"\n>>> 开始处理,请稍候…")
            # 在主线程读取所有控件状态,绝不在后台线程碰 Tk 控件
            arg = before() if before is not None else None
            threading.Thread(target=worker, args=(arg,), daemon=True).start()

        btn = ttk.Button(parent, text="开始执行", command=start)
        btn.pack(pady=6)
        return btn

    def _finish(self, btn, text, error):
        btn.config(state="normal")
        if error is not None:
            self._log(f"[错误] {error}")
            messagebox.showerror("出错了", str(error), parent=self)
        elif text:
            self._log(text)

    def _log(self, text: str):
        self.output.config(state="normal")
        self.output.insert("end", text.rstrip() + "\n")
        self.output.see("end")
        self.output.config(state="disabled")

    @staticmethod
    def _fmt_organize(result) -> str:
        lines = [f"目录:{result['folder']}", f"{'[预览] ' if result['dry_run'] else ''}共 {result['total']} 个文件"]
        for category, items in result["details"].items():
            lines.append(f"[{category}] {len(items)} 个")
            lines += [f"  {it['from']}  ->  {it['to']}" for it in items]
        if result["dry_run"]:
            lines.append("(预览模式,未实际移动)")
        else:
            lines.append(f"[OK] 已移动 {result['total']} 个文件")
        return "\n".join(lines)

    # ------------------------------------------------------------- 各标签页

    def _tab_organize(self, notebook):
        frame = ttk.Frame(notebook, padding=12)
        folder = self._path_row(frame)
        dry = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="预览模式(不实际移动文件)", variable=dry).pack(anchor="w")

        def task(opts):
            folder_path, dry_v = opts
            result = organize(folder_path.strip() or ".", dry_run=dry_v)
            return self._fmt_organize(result)

        self._run_button(frame, task, before=lambda: (folder.get(), dry.get()))
        return frame

    def _tab_rename(self, notebook):
        frame = ttk.Frame(notebook, padding=12)
        folder = self._path_row(frame)

        opts = self._row(frame)
        prefix = tk.StringVar(value="file_")
        suffix = tk.StringVar()
        start = tk.IntVar(value=1)
        padding = tk.IntVar(value=3)
        ttk.Label(opts, text="前缀").pack(side="left")
        ttk.Entry(opts, textvariable=prefix, width=12).pack(side="left", padx=4)
        ttk.Label(opts, text="后缀").pack(side="left")
        ttk.Entry(opts, textvariable=suffix, width=10).pack(side="left", padx=4)
        ttk.Label(opts, text="起始").pack(side="left")
        ttk.Spinbox(opts, from_=0, to=9999, textvariable=start, width=6).pack(side="left", padx=4)
        ttk.Label(opts, text="补零").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=8, textvariable=padding, width=4).pack(side="left", padx=4)

        dry = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="预览模式(不实际重命名)", variable=dry).pack(anchor="w")

        def task(opts):
            folder_path, prefix_v, suffix_v, start_v, padding_v, dry_v = opts
            result = batch_rename(folder_path.strip() or ".", dry_run=dry_v,
                                  prefix=prefix_v, suffix=suffix_v,
                                  start=int(start_v), padding=int(padding_v))
            lines = [f"目录:{result['folder']}"]
            lines += [f"  {c['from']}  ->  {c['to']}" for c in result["changes"]]
            tail = f"{'[预览]' if result['dry_run'] else '[OK]'} 共 {result['total']} 个文件"
            return "\n".join(lines + [tail])

        def collect():
            return (folder.get(), prefix.get(), suffix.get(), start.get(), padding.get(), dry.get())

        self._run_button(frame, task, before=collect)
        return frame

    def _tab_dedupe(self, notebook):
        frame = ttk.Frame(notebook, padding=12)
        folder = self._path_row(frame)
        recursive = tk.BooleanVar()
        ttk.Checkbutton(frame, text="递归子目录", variable=recursive).pack(anchor="w")

        def task(opts):
            folder_path, recursive_v = opts
            result = find_duplicates(folder_path.strip() or ".", recursive=recursive_v)
            if result["group_count"] == 0:
                return "未发现重复文件。"
            lines = [f"发现 {result['group_count']} 组重复,可释放 {_format_bytes(result['wasted_bytes'])}"]
            for digest, paths in result["groups"].items():
                lines.append(f"[{digest[:12]}]")
                for i, path in enumerate(paths):
                    lines.append(f"  {'[保留]' if i == 0 else '[重复]'} {path}")
            return "\n".join(lines)

        self._run_button(frame, task, before=lambda: (folder.get(), recursive.get()))
        return frame

    def _tab_passgen(self, notebook):
        frame = ttk.Frame(notebook, padding=12)
        opts = self._row(frame)
        length = tk.IntVar(value=16)
        count = tk.IntVar(value=5)
        ttk.Label(opts, text="长度").pack(side="left")
        ttk.Spinbox(opts, from_=4, to=128, textvariable=length, width=6).pack(side="left", padx=4)
        ttk.Label(opts, text="数量").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=100, textvariable=count, width=6).pack(side="left", padx=4)

        checks = self._row(frame)
        upper, lower, digits, symbols = (tk.BooleanVar(value=True) for _ in range(4))
        for text, var in (("大写", upper), ("小写", lower), ("数字", digits), ("符号", symbols)):
            ttk.Checkbutton(checks, text=text, variable=var).pack(side="left", padx=4)

        def task(opts):
            length_v, count_v, upper_v, lower_v, digits_v, symbols_v = opts
            passwords = generate_passwords(int(count_v), length=int(length_v), upper=upper_v,
                                           lower=lower_v, digits=digits_v,
                                           symbols=symbols_v)
            return "\n".join(
                f"  {pw}   ({estimate_strength(pw)['label']}, {estimate_strength(pw)['entropy_bits']} bits)"
                for pw in passwords
            )

        def collect():
            return (length.get(), count.get(), upper.get(), lower.get(), digits.get(), symbols.get())

        self._run_button(frame, task, before=collect)
        return frame

    def _tab_stats(self, notebook):
        frame = ttk.Frame(notebook, padding=12)
        input_box = tk.Text(frame, height=6, wrap="word", font=("TkFixedFont", 10))
        input_box.pack(fill="x")

        def task(text):
            if not text.strip():
                return "(请先在上方输入文本)"
            s = text_stats(text)
            return (f"总字符 {s['chars']}  |  去空白 {s['chars_no_space']}  |  中文 {s['cjk_chars']}  |  "
                    f"英文单词 {s['latin_words']}  |  总词数 {s['words']}  |  行数 {s['lines']}  |  "
                    f"UTF-8 字节 {s['bytes_utf8']}")

        # 关键:在主线程读取 Tk 控件,再交给后台线程处理,避免跨线程访问崩溃
        self._run_button(frame, task, before=lambda: input_box.get("1.0", "end").rstrip("\n"))
        return frame


def run() -> None:
    """启动桌面 GUI。"""
    ToolBoxApp().mainloop()
