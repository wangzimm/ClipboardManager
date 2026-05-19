    
"""Application entry point — single instance, DB, tray, window, clipboard monitor."""
import os
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.mime.warning=false")

import sys
import ctypes
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from database import init_db, add_text_item, add_image_item, cleanup_expired, cleanup_recycle, get_items
from monitor import ClipboardMonitor
from settings_manager import get_retention_hours
from ui.card_widget import CARD_STYLE
from ui.tray import TrayManager
from ui.main_window import MainWindow
from ui.settings import SettingsDialog

MUTEX_NAME = "Global\\ClipboardManagerSingleInstance"


def _check_single_instance():
    """Return True if this is the first instance, False if another is already running."""
    kernel32 = ctypes.windll.kernel32
    CreateMutexW = kernel32.CreateMutexW
    CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
    CreateMutexW.restype = wintypes.HANDLE

    handle = CreateMutexW(None, True, MUTEX_NAME)
    error = kernel32.GetLastError()
    # ERROR_ALREADY_EXISTS = 183
    if error == 183:
        if handle:
            kernel32.CloseHandle(handle)
        ctypes.windll.user32.MessageBoxW(
            0,
            "历史粘贴板已在运行中。\n请使用 Ctrl+Shift+V 或点击托盘图标。",
            "提示",
            0x40,
        )
        return False
    return True


class App:
    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setStyleSheet(CARD_STYLE)
        self._app.setQuitOnLastWindowClosed(False)

        init_db()
        retention = get_retention_hours()
        cleanup_expired(retention)
        cleanup_recycle()

        self._window = MainWindow(on_hidden=self._on_hidden, on_exit=self._on_exit)
        self._window.copy_triggered.connect(self._on_copy_from_panel)

        self._monitor = ClipboardMonitor()
        self._monitor.text_copied.connect(self._on_text)
        self._monitor.image_copied.connect(self._on_image)

        self._tray = TrayManager(
            on_show=self._window.toggle_visible,
            on_settings=self._on_settings,
            on_exit=self._on_exit,
        )

        self._app.installNativeEventFilter(self._tray.filter())
        QTimer.singleShot(500, lambda: self._tray.install(int(self._window.winId())))

        self._window.show_dock_initial()

    def _on_text(self, text):
        item_id = add_text_item(text)
        if item_id:
            items = get_items(item_type="text", limit=1, include_image_data=False)
            if items:
                self._window._text_tab.add_card(items[0])

    def _on_image(self, data):
        item_id = add_image_item(data)
        if item_id:
            items = get_items(item_type="image", limit=1)
            if items:
                self._window._image_tab.add_card(items[0])

    def _on_copy_from_panel(self):
        self._monitor.mark_skip_next()

    def _on_hidden(self):
        pass

    def _on_settings(self):
        dialog = SettingsDialog()
        if dialog.exec():
            from database import cleanup_expired
            from settings_manager import get_retention_hours
            cleanup_expired(get_retention_hours())
            self._window.refresh()

    def _on_exit(self):
        try:
            self._tray.uninstall()
        except Exception:
            pass
        self._window.hide()
        self._app.quit()
        sys.exit(0)

    def run(self):
        self._app.exec()


def main():
    if not _check_single_instance():
        sys.exit(0)
    App().run()


if __name__ == "__main__":
    main()
