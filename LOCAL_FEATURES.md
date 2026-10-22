# PicoMD Reader：本地功能与维护说明

## 定位与范围

本仓库是 ReText 的本地 fork，桌面显示名称为 **PicoMD Reader**。它是一个轻量的本地
Markdown 阅读器/编辑器，服务于“打开文件、按章节阅读、少量修改、继续阅读”的场景。

不在范围内：云同步、数据库、知识库、内嵌 PDF 渲染、会话永久恢复，以及 PicoMD 旧二进制
的继续维护。PicoMD 的历史回退二进制不属于本仓库，不能删除。

## 当前功能

### 文档与标签

- 多标签打开 Markdown；关闭最后一个标签时退出。
- 无参数启动时显示文件选择器。
- 单实例模式下，文件管理器双击新的 Markdown 会转发到已有窗口并新开标签。
- 已打开文件在外部被修改时，仅刷新相应标签；标签关闭时回收其文件监听。

### 章节目录与位置

- 左侧只显示当前 Markdown 的章节目录，不显示文件系统目录树。
- 目录识别 `#` 到 `######` 标题，并忽略 fenced code block 内的伪标题。
- 点击目录在阅读或源代码模式中跳至对应标题；正文位置变化时，目录高亮随当前标题更新。
- 每个标签保存一个 Markdown 源代码行号锚点。切换标签、阅读与源代码模式时，以该锚点
  恢复位置。

### 阅读、编辑与本地资源

- `阅读 / 源代码` 在渲染后的 Markdown 和编辑器间切换；手动切到阅读立即请求渲染。
- 切换回阅读时，在目标章节恢复完成后才显示预览，避免先显示顶部再跳回。
- 支持标准 Markdown 本地图片：`![说明](images/example.jpg)`、PNG、JPEG、GIF 与 BMP。
  图片须位于 Markdown 所在目录的相对路径或以绝对路径可访问；不会把剪贴板图片自动
  写入文件。
- 相对 `.md` 链接在应用内打开；相对 `.pdf` 链接交给 Ubuntu 的默认 PDF 阅读器。

### 界面与默认关联

- 顶部精简为：新建、`阅读 / 源代码`、全屏。
- `.desktop` 启动项位于
  `/home/lucious/.local/share/applications/me.mitya57.ReText.desktop`，名称为
  PicoMD Reader，并关联 Markdown MIME 类型。

## 稳定性设计

- 已删除旧文件系统侧栏模块 `ReText/filesystemmodel.py`。
- 已删除旧编辑器/预览双向像素滚动同步模块 `ReText/syncscroll.py`。
- 一个标签任一时刻仅显示源代码编辑器或 WebEngine 阅读预览这一个原生滚动表面；不缓存
  或隐藏另一份完整预览 DOM。
- 位置恢复、渲染和位置索引使用代号校验；文档、标签或渲染改变后，旧的 WebEngine 异步
  回调被拒绝。
- 目录按标题行索引二分定位；滚动导致的目录更新经短暂合并，未改变时不重复刷新 Qt 项。

这些设计降低“跳到顶部、目录与正文不一致、连续切换后滚动失效”的风险，但 GUI 稳定性仍须
以真实 GNOME Wayland 人工验收为准。

## 运行、检查与排障

```bash
cd /home/lucious/Documents/ubuntu_migration_audit/retext/retext
source .venv/bin/activate
retext

python -m compileall -q ReText
python -m unittest discover -q tests
git diff --check
```

仅在排障时启用调试日志：

```bash
RETEXT_DEBUG=1 retext
```

日志记录标签/锚点、渲染代号和位置恢复事件；默认不输出这些调试信息。

真实 GNOME Wayland 验收至少覆盖：长文连续滚动、连续点击章节、A→B→A 标签切换、
阅读/源代码连续切换、相对 `.md`/`.pdf` 链接、外部修改、关闭标签和文件管理器双击新文档。

## 维护约束

- 先用日志和可重复操作确定问题，再修改；不叠加滚轮监听、协议兜底或整页重绘补丁。
- 不自动提交或推送；提交前执行自动检查，推送前确认真实 Wayland 验收结论。
- 正式改动应保持当前轻量阅读器定位，不扩展为编辑器套件或知识库。
