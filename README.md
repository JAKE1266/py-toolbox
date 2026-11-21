# PyToolBox 工具箱

> 一个仓库,四种用法:**Python 库 · 命令行 · 网页版 · 桌面 GUI**
> 全部功能只用 Python 标准库实现,**零第三方依赖**。

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
<!-- 推送到 GitHub 后可启用动态徽章(把 yourname 换成你的用户名):
![CI](https://github.com/yourname/py-toolbox/actions/workflows/ci.yml/badge.svg)
-->

## ✨ 功能

| 功能 | 说明 | CLI | Web | GUI | 库 |
|------|------|:---:|:---:|:---:|:--:|
| 🗂 文件整理 | 按扩展名把散乱文件归入「图片/文档/音频/视频/压缩包/代码」等子目录,支持预览 | ✅ | ✅ | ✅ | ✅ |
| ✏️ 批量重命名 | 统一改为「前缀+序号+后缀」(如 `photo_001.jpg`),自动防覆盖 | ✅ | ✅ | ✅ | ✅ |
| 🔍 重复文件 | 按内容哈希精确查重,先比大小再算哈希,快且省内存 | ✅ | ✅ | ✅ | ✅ |
| 🔑 密码生成 | 基于密码学安全随机源(`secrets`),附强度估算(信息熵) | ✅ | ✅ | ✅ | ✅ |
| 📊 文本统计 | 中英混排友好:英文按词、中文按字,含字节数/行数 | ✅ | ✅ | ✅ | ✅ |

**其他亮点**

- 🚀 **零依赖**:装好 Python 3.9+ 就能跑,无需 `pip install` 任何包
- 🌍 **跨平台**:Windows / macOS / Linux;中文路径、中文界面友好
- 🧪 **带测试**:30 个单元测试 + GitHub Actions 三系统 × 三版本 CI
- 🔒 **安全默认**:网页版只监听 `127.0.0.1`,数据不出本机

## 📦 安装

### 方式一:克隆即用(推荐先体验)

```bash
git clone https://github.com/yourname/py-toolbox.git
cd py-toolbox
python -m pytoolbox --help
```

### 方式二:pip 安装(安装后获得 `pytoolbox` 命令)

```bash
cd py-toolbox
pip install .
```

## 🚀 快速开始

### 1️⃣ 命令行

```bash
# 整理下载文件夹(先预览,再真移)
python -m pytoolbox organize C:/Users/you/Downloads --dry-run
python -m pytoolbox organize C:/Users/you/Downloads

# 批量重命名:travel_001.jpg …
python -m pytoolbox rename ./photos -p travel_ -s _trip

# 查找重复文件
python -m pytoolbox dedupe ./downloads -r

# 生成 3 个 20 位强密码
python -m pytoolbox passgen -l 20 -c 3

# 文本统计
python -m pytoolbox stats article.txt
```

每个命令都支持 `--json`,方便脚本化处理。

### 2️⃣ 网页版

```bash
python -m pytoolbox web        # 自动打开浏览器,默认 http://127.0.0.1:8000
```

深色主题的单页应用,五个工具即点即用;停止服务按 `Ctrl+C`。

### 3️⃣ 桌面 GUI(无需任何依赖,Tkinter 随 Python 自带)

```bash
python -m pytoolbox gui
```

带目录选择器、选项开关与输出日志;文件操作在后台线程执行,界面不卡顿。

### 4️⃣ 当作 Python 库

```python
from pytoolbox import organize, find_duplicates, generate_password, text_stats

organize("C:/Users/you/Downloads", dry_run=True)   # 返回整理计划
find_duplicates("D:/photos", recursive=True)       # {"groups": {...}, "wasted_bytes": ...}
generate_password(20)                              # 'Xk9$mP2#vLq8…'
text_stats("Hello 你好,PyToolBox!")                # {'chars': 18, 'words': 4, ...}
```

## 🧰 命令一览

```
pytoolbox organize  <目录> [-n]      按类型整理文件夹
pytoolbox rename    <目录> [-p 前缀] 批量重命名
pytoolbox dedupe    <目录> [-r]      查找重复文件
pytoolbox passgen   [-l 长度] [-c 个数]  生成强密码
pytoolbox stats     [文件|-]         文本统计
pytoolbox web       [--port 8000]    启动网页版
pytoolbox gui                        启动桌面版
```

## 📁 项目结构

```
py-toolbox/
├── .github/workflows/ci.yml   # CI:Ubuntu / Windows / macOS × Python 3.9-3.13
├── src/pytoolbox/
│   ├── core/                  # 核心功能层(与界面完全解耦)
│   │   ├── organizer.py       #   文件整理
│   │   ├── renamer.py         #   批量重命名
│   │   ├── dedupe.py          #   重复文件
│   │   ├── passgen.py         #   密码生成
│   │   └── textstats.py       #   文本统计
│   ├── templates/index.html   # 网页版界面(单文件,无构建步骤)
│   ├── cli.py                 # 命令行入口(argparse)
│   ├── webapp.py              # 网页版服务(http.server)
│   └── gui.py                 # 桌面版(Tkinter)
├── tests/                     # 单元测试(unittest)
├── pyproject.toml             # 打包配置(可 pip install)
├── LICENSE                    # MIT
└── README.md
```

## 🧪 开发与测试

```bash
# 推荐:先以可编辑模式安装(项目为 src 布局,包在 src/ 下)
python -m pip install -e .
python -m unittest discover -s tests -v

# 不想安装也可临时指定包路径:
# Windows(PowerShell):
$env:PYTHONPATH="src"; python -m unittest discover -s tests -v
# macOS / Linux:
PYTHONPATH=src python -m unittest discover -s tests -v
```

架构上,`core/` 只做纯逻辑、不碰任何界面库,CLI/Web/GUI 三端共享同一实现并各有测试;
新增功能时先写 core 函数,再在三个界面各加一个入口即可。

## ❓ 常见问题

**Q: 为什么零依赖?**
所有能力(`http.server`、`tkinter`、`hashlib`、`secrets`、`argparse`)Python 都自带,
"开箱即用、装完就能跑" 对小工具非常重要,也把供应链风险降到 0。

**Q: 网页版安全吗?**
默认只监听本机回环地址 `127.0.0.1`,局域网内其他设备无法访问。不要用 `--host 0.0.0.0`
对外开放——本工具会执行文件移动等操作,不应暴露给不可信网络。

**Q: 会覆盖我的文件吗?**
整理/重命名遇到同名目标时自动追加「 (1)」等后缀,绝不覆盖;两者都默认
dry-run 预览,确认无误再去掉 `--dry-run` 真正执行。

**Q: 想发布到 PyPI?**
`pytoolbox` 是占位名,发布前请在 `pyproject.toml` 里换一个未被占用的名字
(如 `pytoolbox-kit`),并补上你的用户名与仓库地址。

## 🤝 贡献

欢迎 Issue 与 PR!提交前请:

1. `python -m pip install -e .` 然后 `python -m unittest discover -s tests` 保证测试通过
2. 新功能请附带对应单元测试
3. 保持「core 纯逻辑、界面薄壳」的分层结构

## 📄 许可证

[MIT](LICENSE) —— 可自由使用、修改与分发。
