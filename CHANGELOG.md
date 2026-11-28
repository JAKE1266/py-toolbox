# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式,
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.1] - 2026-11-28

### 修复
- 网页版 API 增加每次启动随机访问令牌、Host/Origin 同源校验,未授权请求不会解析请求体或执行文件操作
- 所有网页响应增加防点击劫持、MIME 嗅探、引用泄漏与 CSP 安全头
- 网页密码列表改用 DOM 文本节点渲染,不再把返回值拼入 `innerHTML`
- 命令行标准输入输出统一 UTF-8,修复旧编码控制台下的中文乱码或编码异常

### 改进
- CI 改为构建 wheel/sdist 后,在仓库外安装真实 wheel 并运行已安装冒烟与全部测试
- CI 覆盖 Ubuntu / Windows / macOS × Python 3.9 / 3.10 / 3.12 / 3.13
- sdist 包含更新日志与完整测试文件;单元测试增至 39 项

## [1.0.0] - 2026-11-21

### 新增
- 核心功能库(纯标准库实现):
  - `organize` 按类型整理文件夹(图片/文档/音频/视频/压缩包/代码)
  - `batch_rename` 批量重命名(前缀 + 序号,自动防冲突)
  - `find_duplicates` 按内容哈希查找重复文件(先比大小再算哈希)
  - `generate_password` / `estimate_strength` 密码生成与强度估算
  - `text_stats` 中英混排文本统计
- 三种界面:命令行 `pytoolbox`、本地网页版 `python -m pytoolbox web`、桌面版 `python -m pytoolbox gui`
- 30 个单元测试;GitHub Actions 三系统 × 三 Python 版本持续集成
