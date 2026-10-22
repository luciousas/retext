# PicoMD Reader（本地 ReText fork）

这是为 Ubuntu GNOME Wayland 本地使用维护的轻量 Markdown 阅读器与编辑器。它以
[ReText 8.1.0](https://github.com/retext-project/retext) 为上游基础，保留 Markdown
编辑和渲染能力，并针对长文阅读重构了章节导航、阅读/源代码切换和位置恢复。

本仓库不是 PicoMD 的源码，也不是知识库、同步服务或 PDF 阅读器。目标是稳定地打开本地
Markdown，阅读、编辑并在章节间导航。

## 本 fork 的功能

- 多标签 Markdown 文档；关闭最后一个标签即退出，不保存会话。
- 左侧仅显示当前文档的 Markdown 标题目录（`#` 至 `######`），可点击跳转。
- 顶部保留新建、`阅读 / 源代码`、全屏三个常用入口。
- 阅读和源代码切换按当前标题位置恢复，不依赖不稳定的像素滚动位置。
- 相对路径 Markdown 链接在程序内打开；相对路径 PDF 链接交给系统默认阅读器。
- 支持本地图片，例如 `![示例](images/example.png)`。
- 外部修改文件后仅刷新对应标签；文件管理器双击 Markdown 会转发到已有窗口。
- GNOME 桌面启动项名称为 **PicoMD Reader**，并关联 `text/markdown` 与
  `text/x-markdown`。

完整的功能边界、稳定性设计、调试日志和 GNOME Wayland 验收清单见
[LOCAL_FEATURES.md](LOCAL_FEATURES.md)。配置项说明见
[configuration.md](configuration.md)。

## 本机运行

```bash
cd /home/lucious/Documents/ubuntu_migration_audit/retext/retext
source .venv/bin/activate
retext
```

从头创建开发环境（Python 3.9 或更高版本）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[webengine]'
retext
```

运行自动检查：

```bash
python -m compileall -q ReText
python -m unittest discover -q tests
git diff --check
```

## Markdown 图片与链接

图片必须是本地可访问文件。推荐把图片放在 Markdown 同级目录或子目录：

```markdown
![部署示意](images/deployment.png)
[下一篇](next.md)
[查看附件](appendix.pdf)
```

`next.md` 在本程序中新标签打开；`appendix.pdf` 由 Ubuntu 的默认 PDF 阅读器打开。

## 稳定性与维护原则

旧版“编辑器与预览双向像素滚动同步”及文件系统侧栏已移除。当前每个标签只显示一个原生
滚动表面，并以 Markdown 源代码行号作为目录、阅读和编辑之间的共同位置锚点。WebEngine
异步回调带版本校验，过期回调不能覆盖当前标签或当前位置。

功能修改后必须在真实 GNOME Wayland 会话中验证长文滚动、连续目录点击、标签切换、
阅读/源代码切换、外部文件修改和本地链接。不要用额外滚轮监听、整页重绘或隐藏 DOM 的
补丁掩盖滚动问题。

## 上游、许可与致谢

本 fork 保留 ReText 的 GPL v2+ 许可，详见 [LICENSE_GPL](LICENSE_GPL)。上游 ReText
版权归 Dmitry Shachnev、Maurice van der Pot 及贡献者所有；本地维护改动记录在
[changelog.md](changelog.md)。图标许可说明见 [ReText/icons/README.md](ReText/icons/README.md)。
