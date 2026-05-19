# 技术方案

## 技术栈

| 层面 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 开发效率高，生态丰富 |
| UI 框架 | PySide6 | Qt 的 Python 绑定，Windows 原生体验好 |
| 数据库 | SQLite | 轻量嵌入式，无需安装服务 |
| 打包 | PyInstaller | 将 Python 应用打包为单文件 .exe |
| 剪贴板 | PySide6 QClipboard | 框架内置，无需额外库 |

## 架构设计

### 模块划分

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  monitor.py │───>│ database.py │<───│    UI 层    │
│ (剪贴板监控) │    │ (数据持久化) │    │ (展示/交互) │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                 ┌────────┴────────┐
                 │ settings_manager│
                 │   (设置管理)     │
                 └─────────────────┘
```

### 数据流

1. **写入流**：用户 Ctrl+C → 剪贴板变化 → monitor.py 检测 → database.py 写入 SQLite
2. **读取流**：用户呼出面板 → UI 从 database.py 查询 → 渲染卡片列表
3. **回写流**：用户点击卡片 → database.py 读取内容 → 写回剪贴板

### 线程模型

- 主线程：PySide6 事件循环 + UI 渲染
- 监控线程：定时轮询剪贴板（200ms 间隔），检测变化后通过信号通知主线程

## 数据库

### 数据库文件位置

`%APPDATA%/ClipboardManager/clipboard.db`

### 表结构

```sql
CREATE TABLE clipboard_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,          -- 'text' | 'image'
    content TEXT,                -- 文字内容
    image_data BLOB,             -- PNG 格式图片二进制
    pinned INTEGER DEFAULT 0,    -- 0=普通 1=置顶
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### 索引

```sql
CREATE INDEX idx_type ON clipboard_items(type);
CREATE INDEX idx_created ON clipboard_items(created_at);
CREATE INDEX idx_pinned ON clipboard_items(pinned);
```

## 打包方案

使用 PyInstaller 打包为单文件 .exe，配置如下：
- `--onefile`：单文件输出
- `--windowed`：无控制台窗口
- `--icon resources/icon.ico`：应用图标
- `--add-data`：打包 SQLite DLL 等依赖

输出路径：`dist/历史粘贴板.exe`

## 开机启动

通过 Windows 注册表实现：
- 路径：`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
- 键名：`ClipboardManager`
- 键值：exe 文件路径
