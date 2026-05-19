<!-- 截图占位：录屏 GIF 放在此处 -->
<!-- <p align="center"><img src="docs/demo.gif" width="600"></p> -->

<p align="center">
  <img src="resources/icon.ico" width="64">
</p>

<h1 align="center">历史粘贴板</h1>
<p align="center">Windows 桌面剪贴板管理器 —— 自动记录，随时找回</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue">
  <img src="https://img.shields.io/badge/python-3.14-blue">
  <img src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## 它能做什么

日常工作中，复制的内容常常被覆盖后就找不回来。历史粘贴板在后台自动记录每一次复制，当你需要之前的某段文字或某张截图时，按 `Ctrl+Shift+V` 呼出面板，搜索、点击即可写回剪贴板。

| 场景 | 痛点 | 解决方案 |
|------|------|----------|
| 频繁 Ctrl+C | 上一次复制的内容被覆盖 | 自动记录所有历史 |
| 找截图 | 微信/QQ 聊天记录翻半天 | 图片历史统一管理 |
| 重复粘贴 | 同一段话反复写 | 置顶 + 一键回写 |
| 隐私顾虑 | 担心数据上传云端 | 纯本地 SQLite 存储 |

## 功能一览

- **文字 & 图片记录** — 自动捕获剪贴板文字和图片，时间倒序排列
- **全局热键** — `Ctrl+Shift+V` 呼出，`Esc` 隐藏，无需离开当前窗口
- **搜索过滤** — 输入关键词即时筛选历史记录
- **置顶** — 高频内容钉在列表顶部，不受过期清理影响
- **回收站** — 软删除机制，误删可恢复，7 天后自动清除
- **手动清理** — 按时间范围 + 方向（早于/晚于）批量删除
- **边缘浮动图标** — 48px 方块缩为 8px 细条，靠边不挡视线，触碰即展开
- **开机自启动** — 注册表写入，重启电脑也不错过剪贴板内容
- **纯本地** — SQLite 存在 `%APPDATA%`，数据不外传

## 快速开始

### 直接下载（推荐）

前往 [Releases](../../releases) 下载最新 `历史粘贴板.exe`，双击运行即可。

### 从源码运行

```bash
pip install -r requirements.txt
python src/main.py
```

### 打包

```bash
pyinstaller build.spec
# 输出: dist/历史粘贴板.exe
```

## 操作指南

| 操作 | 方式 |
|------|------|
| 呼出 / 隐藏面板 | `Ctrl+Shift+V` / `Esc` |
| 复制历史内容 | 点击卡片 |
| 置顶 / 取消置顶 | 右键卡片 |
| 删除 | 右键卡片 → 删除（进入回收站） |
| 搜索 | 面板顶部搜索框 |
| 修改保留时间 | 右键托盘图标 → 设置 |
| 手动清理 | 面板底部「清理」按钮 |
| 回收站 | 面板底部「回收站」按钮 |
| 移动边缘图标 | 拖拽浮动图标到屏幕任意边缘 |

## 项目结构

```
src/
├── main.py              # 入口：单实例检查、信号连接
├── database.py          # SQLite CRUD、回收站、清理
├── monitor.py           # QClipboard 200ms 轮询
├── settings_manager.py  # 保留时间 + 开机自启动
└── ui/
    ├── main_window.py   # 主面板布局
    ├── tray.py          # Win32 原生托盘 + 全局热键
    ├── dock_widget.py   # 边缘浮动图标
    ├── text_tab.py      # 文字列表
    ├── image_tab.py     # 图片列表
    ├── search_bar.py    # 搜索框
    ├── settings.py      # 设置对话框
    ├── cleanup_dialog.py# 手动清理
    └── recycle_bin.py   # 回收站
```

## 技术栈

| 层 | 技术 |
|----|------|
| UI 框架 | PySide6 6.5+ |
| 数据库 | SQLite |
| 系统托盘 | 原生 Win32 `Shell_NotifyIcon`（非 QSystemTrayIcon） |
| 剪贴板监控 | QClipboard 200ms 轮询 |
| 打包 | PyInstaller 单文件 exe |

## 常见问题

<details>
<summary><b>为什么复制的内容没出现？</b></summary>
确认托盘图标存在（软件正在运行），然后按 Ctrl+Shift+V 打开面板查看。
</details>

<details>
<summary><b>置顶内容会被自动清理吗？</b></summary>
不会。置顶标记的内容不受保留时间限制，永久保留。
</details>

<details>
<summary><b>数据存在哪里？安全吗？</b></summary>
数据存于 <code>%APPDATA%\ClipboardManager\clipboard.db</code>，纯本地 SQLite 文件，不联网。
</details>

<details>
<summary><b>如何关闭开机启动？</b></summary>
右键托盘图标 → 设置 → 取消「开机自动启动」→ 保存。
</details>

<details>
<summary><b>能同步到其他设备吗？</b></summary>
当前版本不支持。数据纯本地存储，如需跨设备使用可自行同步 clipboard.db 文件。
</details>
