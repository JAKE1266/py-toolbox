# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式,
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
