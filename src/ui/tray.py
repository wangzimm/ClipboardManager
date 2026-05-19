"""System tray + global hotkey — Win32 Shell_NotifyIcon with Qt native event filter."""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtGui import QPainter, QColor, QPixmap, QCursor, QAction
from PySide6.QtWidgets import QMenu

# ── Win32 constants ───────────────────────────────────────────────
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_V = 0x56
HOTKEY_ID = 1

NIM_ADD = 0
NIM_DELETE = 2
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040

_user32 = ctypes.windll.user32
_shell32 = ctypes.windll.shell32


# Minimal NOTIFYICONDATAW — only fields known to Shell_NotifyIcon classic API.
# Using the extended struct causes alignment issues on some 64-bit systems.
class NID(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
    ]


def _register_hotkey(hwnd):
    _user32.RegisterHotKey(wintypes.HWND(hwnd), HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_V)


def _unregister_hotkey(hwnd):
    _user32.UnregisterHotKey(wintypes.HWND(hwnd), HOTKEY_ID)


# ── Native event filter ───────────────────────────────────────────
class _TrayFilter(QAbstractNativeEventFilter):
    def __init__(self):
        super().__init__()
        self.tray_msg_id = None  # set after RegisterWindowMessage
        self.on_left = None
        self.on_right = None

    def nativeEventFilter(self, event_type, message):
        msg = ctypes.cast(ctypes.c_void_p(int(message)), ctypes.POINTER(wintypes.MSG))
        m = msg.contents
        if m.message == WM_HOTKEY and m.wParam == HOTKEY_ID:
            if self.on_left:
                self.on_left()
            return True, 0
        if self.tray_msg_id and m.message == self.tray_msg_id:
            if m.wParam == 1 and m.lParam == 0x0202 and self.on_left:  # WM_LBUTTONUP
                self.on_left()
                return True, 0
            if m.wParam == 1 and m.lParam == 0x0205 and self.on_right:  # WM_RBUTTONUP
                self.on_right()
                return True, 0
        return False, 0


# ── TrayManager ───────────────────────────────────────────────────
class TrayManager:
    def __init__(self, on_show, on_settings, on_exit):
        self._hwnd = 0
        self._hicon = None
        self._added = False
        self._msg_id = None

        from settings_manager import get_auto_start, set_auto_start

        # Build context menu
        self._menu = QMenu()

        act = self._menu.addAction("显示面板")
        act.triggered.connect(on_show)

        act = self._menu.addAction("设置")
        act.triggered.connect(on_settings)

        self._menu.addSeparator()

        self._auto_start_action = self._menu.addAction("开机自启动")
        self._auto_start_action.setCheckable(True)
        self._auto_start_action.triggered.connect(
            lambda checked: set_auto_start(checked)
        )

        self._menu.addSeparator()

        act = self._menu.addAction("退出")
        act.triggered.connect(on_exit)

        # Refresh auto-start check state each time menu is about to show
        self._menu.aboutToShow.connect(
            lambda: self._auto_start_action.setChecked(get_auto_start())
        )

        # Native event filter for hotkey + tray clicks
        self._filter = _TrayFilter()
        self._filter.on_left = lambda: on_show()
        self._filter.on_right = lambda: self._menu.popup(QCursor.pos())

    def install(self, win_id):
        hwnd = int(win_id)
        self._hwnd = hwnd

        # Hotkey
        _register_hotkey(hwnd)

        # Unique callback message ID via RegisterWindowMessage
        self._msg_id = _user32.RegisterWindowMessageW("ClipboardManagerTrayV2")
        self._filter.tray_msg_id = self._msg_id

        # Create icon from temp .ico file (much more reliable than GDI-HICON assembly)
        import os
        icon_path = os.path.join(os.environ["TEMP"], "_cm_tray.ico")
        self._make_icon_file(icon_path)

        _user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                        ctypes.c_int, ctypes.c_int, wintypes.UINT]
        _user32.LoadImageW.restype = wintypes.HANDLE
        _user32.DestroyIcon.argtypes = [wintypes.HICON]

        self._hicon = _user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0,
                                          LR_LOADFROMFILE | LR_DEFAULTSIZE)

        # Add tray icon
        _shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NID)]
        _shell32.Shell_NotifyIconW.restype = wintypes.BOOL

        nid = NID()
        nid.cbSize = ctypes.sizeof(NID)
        nid.hWnd = wintypes.HWND(hwnd)
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = self._msg_id
        nid.hIcon = self._hicon
        nid.szTip = "历史粘贴板"
        _shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        self._added = True

    def _make_icon_file(self, path):
        px = QPixmap(32, 32)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#64B5F6"))
        p.setPen(QColor("#1E88E5"))
        p.drawRoundedRect(4, 2, 24, 28, 4, 4)
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(8, 8, 10, 3, 1, 1)
        p.drawRoundedRect(8, 13, 6, 3, 1, 1)
        p.setBrush(QColor("#BBDEFB"))
        p.drawRoundedRect(9, 19, 3, 4, 1, 1)
        p.end()
        px.save(path, "ICO")

    def uninstall(self):
        if self._added and self._hwnd:
            nid = NID()
            nid.cbSize = ctypes.sizeof(NID)
            nid.hWnd = wintypes.HWND(self._hwnd)
            nid.uID = 1
            _shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            self._added = False
        if self._hwnd:
            _unregister_hotkey(self._hwnd)
        if self._hicon:
            _user32.DestroyIcon(self._hicon)
            self._hicon = None

    def filter(self):
        return self._filter
