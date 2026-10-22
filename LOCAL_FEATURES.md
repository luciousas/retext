# 本地 fork：PicoMD Reader 功能与维护说明

本仓库是 ReText 的个人本地 fork，用作轻量 Markdown 阅读器与编辑器；它不是
PicoMD 的源码，也不尝试扩展为知识库或笔记同步软件。

## 当前功能

- 多标签打开 Markdown；关闭最后一个标签即退出，不保存会话。
- 左侧仅显示当前 Markdown 文档的章节目录。目录来自 `#` 至 `######` 标题，
  忽略 fenced code block 中的伪标题；不再显示文件系统目录树。
- 点击章节目录可跳转到对应的源代码或阅读位置。滚动正文时，目录会按标题更新。
- 顶部仅保留：新建、`阅读 / 源代码`、全屏。`阅读 / 源代码` 在源代码与渲染
  Markdown 间切换，使用每个标签独立的章节锚点保存位置。
- 从源代码切换到阅读时，先完成 Markdown 渲染及目标章节滚动，再显示预览，避免
  短暂显示旧预览的顶部位置。
- 本地相对 Markdown 链接在应用内打开；本地 PDF 链接交给系统默认 PDF 阅读器。
- 支持 Markdown 图片语法，例如 `![说明](images/example.png)`；图片文件必须可由
  Markdown 文件所在目录的相对路径或绝对路径访问。
- 文件被外部修改后会刷新对应标签；标签关闭时会解除对应文件监听。
- 单实例启动：文件管理器双击新的 Markdown 文档会转发到已有窗口并作为标签打开。
- 无参数启动显示 Markdown 文件选择器；默认 MIME 关联由
  `me.mitya57.ReText.desktop` 提供。

## 稳定性设计

- 旧的编辑器/预览双向滚动同步已删除。一个标签只显示一个原生滚动表面：源代码
  编辑器或 WebEngine 阅读预览。
- 标签保存的是 Markdown 源代码行号锚点，而不是不稳定的像素值。
- WebEngine 的渲染、位置索引、滚动恢复均带代号；旧页面的异步回调不会覆盖当前状态。
- 阅读/源代码切换与外部文件刷新会使旧位置事件失效；目录更新经过 80ms 合并。
- 编辑时的预览转换使用 500ms 防抖；用户手动切换到阅读时立即转换，不额外等待。
- 章节目录使用标题行索引二分定位，并跳过未变化的 Qt 更新；重建目录期间暂停绘制。

## 运行和维护

开发环境入口：

```bash
cd /home/lucious/Documents/ubuntu_migration_audit/retext/retext
source .venv/bin/activate
retext
```

常规验证：

```bash
python -m compileall -q ReText
python -m unittest discover -q tests
git diff --check
```

真实 GNOME Wayland 验收应覆盖：长文滚动、连续章节点击、A→B→A 标签切换、
阅读/源代码连续切换、相对 `.md` 与 `.pdf` 链接、文件外部修改、关闭标签，以及
文件管理器双击新 Markdown。

仅排障时可启用紧凑日志：

```bash
RETEXT_DEBUG=1 retext
```

该环境变量会记录锚点、渲染代号和位置恢复事件；默认不输出这些日志。

## 保留边界

- 不自动提交或推送，除非维护者明确要求。
- PicoMD 的历史二进制回退副本不属于本仓库，且不得删除。
- PDF 仍使用系统默认阅读器；本 fork 不嵌入 PDF 渲染器。
