# CLAUDE.md - 历史粘贴板项目指引

## 项目简介

Windows 桌面剪贴板管理软件，Python + PySide6 + SQLite。自动记录文字和图片复制历史，支持搜索、置顶、回收站、手动清理。全局热键 `Ctrl+Shift+V` 呼出面板。

## 技术要点

- **UI 框架**：PySide6 6.5+，信号/槽机制
- **系统托盘**：原生 Win32 `Shell_NotifyIcon`，**不是** `QSystemTrayIcon`（Win11 上有 bug）
- **数据库**：SQLite → `%APPDATA%/ClipboardManager/clipboard.db`
- **剪贴板监控**：QClipboard 200ms 轮询
- **打包**：PyInstaller 单文件 .exe → `dist/历史粘贴板.exe`
- **开机启动**：注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ClipboardManager`

## 项目结构

```
src/
├── main.py              # 入口：单实例检查(Mutex)、初始化、信号连接
├── database.py          # 所有 SQLite 操作（CRUD、清理、回收站）
├── monitor.py           # QClipboard 轮询监控
├── settings_manager.py  # 保留时间(小时) + 开机自启动(注册表)
└── ui/
    ├── main_window.py   # 主面板：标题栏、搜索、标签页、底部按钮
    ├── tray.py          # Win32 托盘图标 + 全局热键 Ctrl+Shift+V
    ├── dock_widget.py   # 边缘浮动图标（48×48 → 2.5s → 8px细边）
    ├── text_tab.py      # 文字列表标签页
    ├── image_tab.py     # 图片列表标签页
    ├── search_bar.py    # 搜索输入框
    ├── settings.py      # 设置对话框（保留时间 + 开机自启动）
    ├── cleanup_dialog.py# 手动清理：时间 + 方向（早于/晚于）
    └── recycle_bin.py   # 回收站对话框（恢复/永久删除）
```

## 关键架构细节

### 托盘（tray.py）

QSystemTrayIcon 在 Win11 上右键菜单不弹出，改用原生 Win32 API：
- `RegisterWindowMessage("ClipboardManagerTrayV2")` 获取唯一消息 ID
- `NOTIFYICONDATAW` 只用基础字段（cbSize ~ szTip），扩展字段会导致 64 位对齐偏移
- `QAbstractNativeEventFilter` 拦截 Win32 消息
- 图标：`QPixmap` 绘制 → 临时 `.ico` → `LoadImageW` → HICON
- 菜单绑定：`act = menu.addAction("文字")` 然后 `act.triggered.connect(cb)`，不能 `addAction(text, cb)`

### 边缘图标（dock_widget.py）

双状态自动切换：
- 正常：48×48 圆角方块，带剪贴板图标
- 2.5 秒无鼠标悬浮 → 缩为 8×56 细边条
- 鼠标触碰细边 → 即刻展开恢复
- 点击图标 → 恢复主面板，可拖动

### 数据库（database.py）

- 重复内容通过 `content_hash`(MD5) 去重，更新时间戳
- 删除 = 先 INSERT INTO recycle_bin 再 DELETE（软删除）
- 回收站条目 7 天后自动清除
- `cleanup_expired(hours, direction)` — direction 可选 "older"/"newer"

### 保留时间（settings_manager.py）

8 档：1h、3h、6h、12h、1天、3天、5天、7天，默认 72h

## 开发命令

```bash
pip install -r requirements.txt    # 安装依赖
python src/main.py                 # 运行
pyinstaller build.spec             # 打包
taskkill /f /im "历史粘贴板.exe"    # 停止旧进程
```

## 环境

Python 3.14.3 / PySide6 6.5+ / PyInstaller 6.20.0 / Windows 11 Home China 10.0.26200
