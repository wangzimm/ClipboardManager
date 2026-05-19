"""Main popup panel — frameless, drag-movable, manually resizable."""
from PySide6.QtCore import Qt, QPoint, QTimer, Signal, QRect
from PySide6.QtGui import QMouseEvent, QCursor, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QApplication,
    QPushButton, QMenu,
)

from ui.search_bar import SearchBar
from ui.text_tab import TextTab
from ui.image_tab import ImageTab
from ui.favorite_tab import FavoriteTab
from ui.dock_widget import DockWidget
from ui.recycle_bin import RecycleBinDialog
from ui.cleanup_dialog import CleanupDialog

EDGE = 6
WA_INACTIVE = 0

STYLE = """
QWidget#mainPanel {
    background-color: #E3F2FD;
    border: 1px solid #BBDEFB;
    border-radius: 8px;
}
QTabWidget {
    background-color: #E3F2FD;
    border: none;
}
QTabWidget::pane {
    background-color: #E3F2FD;
    border: none;
}
QTabBar::tab {
    background: #E3F2FD;
    color: #757575;
    padding: 6px 24px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: #90CAF9;
    color: #0D47A1;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: #BBDEFB;
    color: #424242;
}
QLabel#titleLabel {
    color: #424242;
    font-size: 14px;
    font-weight: bold;
    padding: 4px 0;
}
QScrollArea {
    border: none;
    background: #E3F2FD;
}
"""


class MainWindow(QWidget):
    copy_triggered = Signal()

    def __init__(self, on_hidden=None, on_exit=None):
        super().__init__(None)
        self._on_hidden = on_hidden
        self._on_exit = on_exit
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_pos = None
        self._initial_show = True
        self._docked = False
        self._maximized = False
        self._normal_geo = None

        self._dock = DockWidget()
        self._dock.restore_requested.connect(self._restore_from_dock)

        self.setObjectName("mainPanel")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setStyleSheet(STYLE)
        self.setMinimumSize(300, 400)
        self.resize(300, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)

        # Title bar
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(9, 8, 9, 4)
        title = QLabel("历史粘贴板")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        # Maximize button
        self._max_btn = QPushButton("□")
        self._max_btn.setObjectName("maxBtn")
        self._max_btn.setFixedSize(24, 24)
        self._max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._max_btn.setToolTip("全屏放大")
        self._max_btn.clicked.connect(self._toggle_maximize)
        self._max_btn.setStyleSheet("""
            QPushButton#maxBtn {
                background: transparent;
                border: none;
                color: #757575;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton#maxBtn:hover {
                background: #BBDEFB;
                color: #1E88E5;
            }
        """)
        title_bar.addWidget(self._max_btn)

        # Hide-to-tray button
        self._tray_btn = QPushButton("−")
        self._tray_btn.setObjectName("trayBtn")
        self._tray_btn.setFixedSize(24, 24)
        self._tray_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tray_btn.setToolTip("隐藏到系统托盘")
        self._tray_btn.clicked.connect(self.hide)
        self._tray_btn.setStyleSheet("""
            QPushButton#trayBtn {
                background: transparent;
                border: none;
                color: #757575;
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton#trayBtn:hover {
                background: #BBDEFB;
                color: #1E88E5;
            }
        """)
        title_bar.addWidget(self._tray_btn)

        # Close button
        self._close_btn = QPushButton("×")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._show_close_menu)
        self._close_btn.setStyleSheet("""
            QPushButton#closeBtn {
                background: transparent;
                border: none;
                color: #757575;
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton#closeBtn:hover {
                background: #FFCDD2;
                color: #C62828;
            }
        """)
        title_bar.addWidget(self._close_btn)
        layout.addLayout(title_bar)

        # Search bar
        search_container = QHBoxLayout()
        search_container.setContentsMargins(5, 2, 5, 4)
        self._search = SearchBar()
        self._search.search_changed.connect(self._on_search)
        search_container.addWidget(self._search)
        layout.addLayout(search_container)

        # Tab widget
        self._tabs = QTabWidget()
        self._text_tab = TextTab()
        self._image_tab = ImageTab()
        self._favorite_tab = FavoriteTab()

        self._text_tab.copy_triggered.connect(self.copy_triggered.emit)
        self._image_tab.copy_triggered.connect(self.copy_triggered.emit)
        self._favorite_tab.copy_triggered.connect(self.copy_triggered.emit)

        self._text_tab.favorites_changed.connect(self._favorite_tab.refresh)
        self._image_tab.favorites_changed.connect(self._favorite_tab.refresh)

        self._tabs.addTab(self._text_tab, "文字")
        self._tabs.addTab(self._image_tab, "图片")
        self._tabs.addTab(self._favorite_tab, "收藏")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, stretch=1)

        # Bottom bar
        bottom = QHBoxLayout()
        bottom.setContentsMargins(9, 4, 9, 4)

        self._clean_btn = QPushButton("清理")
        self._clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clean_btn.setStyleSheet("""
            QPushButton {
                background: #FFF3E0; border: 1px solid #FFCC80;
                border-radius: 4px; padding: 3px 10px; color: #E65100;
                font-size: 11px;
            }
            QPushButton:hover { background: #FFE0B2; }
        """)
        self._clean_btn.clicked.connect(self._show_cleanup)
        bottom.addWidget(self._clean_btn)

        self._recycle_btn = QPushButton("回收站")
        self._recycle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._recycle_btn.setStyleSheet("""
            QPushButton {
                background: #FFEBEE; border: 1px solid #FFCDD2;
                border-radius: 4px; padding: 3px 10px; color: #C62828;
                font-size: 11px;
            }
            QPushButton:hover { background: #FFCDD2; }
        """)
        self._recycle_btn.clicked.connect(self._show_recycle_bin)
        bottom.addWidget(self._recycle_btn)

        bottom.addStretch()
        hint = QLabel("Ctrl+Shift+V 呼出 | Esc 隐藏")
        hint.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        bottom.addWidget(hint)
        layout.addLayout(bottom)

    def _on_search(self, keyword):
        self._text_tab.set_search(keyword)

    def _refresh_visible(self):
        tab = self._tabs.currentWidget()
        if tab and not tab._loaded:
            tab.refresh()

    def _on_tab_changed(self, index):
        tab = self._tabs.widget(index)
        if tab and not tab._loaded:
            tab.refresh()
        # Always refresh favorites tab when switching to it
        if tab is self._favorite_tab:
            tab.refresh()

    def refresh(self):
        self._text_tab.refresh()
        self._image_tab.refresh()
        self._favorite_tab.refresh()

    def show_dock_initial(self):
        """Show the dock tab on startup without showing the main panel."""
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self._docked = True
        self._dock.place_at(geo.top() + 200)

    def show_at_cursor(self):
        if self._initial_show:
            screen = QApplication.primaryScreen()
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 20
            y = geo.top() + 20
            self.move(QPoint(x, y))
            self._initial_show = False

        self._search.clear()
        self._text_tab.refresh()

        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_visible(self):
        if self._docked:
            self._restore_from_dock()
        elif self.isVisible():
            self.hide()
        else:
            self.show_at_cursor()

    # ── edge detection ──
    def _detect_edge(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()

        left = x < EDGE
        right = x > w - EDGE
        top = y < EDGE
        bottom = y > h - EDGE

        if top and left: return "nw"
        if top and right: return "ne"
        if bottom and left: return "sw"
        if bottom and right: return "se"
        if left: return "w"
        if right: return "e"
        if top: return "n"
        if bottom: return "s"
        return None

    def _edge_cursor(self, edge):
        if edge in ("n", "s"):
            return Qt.CursorShape.SizeVerCursor
        if edge in ("e", "w"):
            return Qt.CursorShape.SizeHorCursor
        if edge in ("ne", "sw"):
            return Qt.CursorShape.SizeBDiagCursor
        if edge in ("nw", "se"):
            return Qt.CursorShape.SizeFDiagCursor
        return Qt.CursorShape.ArrowCursor

    # ── mouse events: move + resize ──
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            edge = self._detect_edge(pos)
            if edge and pos.y() >= 32:
                self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                event.accept()
                return
            if pos.y() < 32:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        if self._resize_edge is not None:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = QRect(self._resize_start_geo)
            self._apply_resize(geo, delta)
            event.accept()
            return
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        # Update cursor for edges
        edge = self._detect_edge(pos)
        if edge and pos.y() >= 32:
            self.setCursor(self._edge_cursor(edge))
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        was_dragging = self._drag_pos is not None
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_geo = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if was_dragging:
            self._try_dock()
        super().mouseReleaseEvent(event)

    def _apply_resize(self, geo, delta):
        e = self._resize_edge
        if "e" in e:
            geo.setRight(geo.right() + delta.x())
        if "w" in e:
            geo.setLeft(geo.left() + delta.x())
        if "s" in e:
            geo.setBottom(geo.bottom() + delta.y())
        if "n" in e:
            geo.setTop(geo.top() + delta.y())

        mini = self.minimumSize()
        if geo.width() < mini.width():
            if "e" in e:
                geo.setRight(geo.left() + mini.width())
            else:
                geo.setLeft(geo.right() - mini.width())
        if geo.height() < mini.height():
            if "s" in e:
                geo.setBottom(geo.top() + mini.height())
            else:
                geo.setTop(geo.bottom() - mini.height())

        self.setGeometry(geo)

    # ── edge docking ─────────────────────────────────────────────
    def _try_dock(self):
        """If the window is mostly off-screen, dock it to the nearest edge."""
        wg = self.frameGeometry()
        screen = QApplication.screenAt(wg.center())
        if screen is None:
            screen = QApplication.primaryScreen()
        sg = screen.availableGeometry()

        intersection = sg.intersected(wg)
        if intersection.isNull():
            self._do_dock(wg)
            return

        # If more than 1/3 of the window is off-screen, dock it
        visible_area = intersection.width() * intersection.height()
        total_area = wg.width() * wg.height()
        if total_area > 0 and visible_area / total_area < 0.67:
            self._do_dock(wg)

    def _do_dock(self, wg):
        """Hide panel and show dock tab at the right screen edge."""
        self._docked = True
        self._dock.place_at(wg.center().y())
        self.hide()

    def _restore_from_dock(self):
        """Hide dock indicator and restore the main panel at top-right."""
        self._dock.hide()
        self._docked = False
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(QPoint(geo.right() - self.width() - 20, geo.top() + 20))
        self._search.clear()
        self._refresh_visible()
        self.show()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        """When window hides and not already docked, show the edge dock tab."""
        super().hideEvent(event)
        if not self._docked and self.isVisible() is False:
            self._dock.place_at(self.frameGeometry().center().y())
            self._docked = True

    # ── deactivate → hide to dock ────────────────────────────────
    def nativeEvent(self, event_type, message):
        """Catch WM_ACTIVATE(WA_INACTIVE) so WA_ShowWithoutActivating
        doesn't block focus-out detection."""
        import ctypes
        from ctypes import wintypes
        msg = ctypes.cast(ctypes.c_void_p(int(message)), ctypes.POINTER(wintypes.MSG)).contents
        if msg.message == 0x0006 and msg.wParam == WA_INACTIVE:  # WM_ACTIVATE
            QTimer.singleShot(200, self._on_deactivate)
        return False, 0

    def _on_deactivate(self):
        if self.isVisible():
            if QApplication.activePopupWidget() or QApplication.activeModalWidget():
                return
            pos = QCursor.pos()
            if not self.geometry().contains(pos):
                self.hide()

    def _show_close_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 24px;
                color: #424242;
            }
            QMenu::item:selected {
                background: #E3F2FD;
                color: #1E88E5;
            }
        """)

        hide_action = QAction("隐藏到托盘", menu)
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)

        menu.addSeparator()

        quit_action = QAction("退出程序", menu)
        quit_action.triggered.connect(self._on_exit if self._on_exit else QApplication.quit)
        menu.addAction(quit_action)

        pos = self._close_btn.mapToGlobal(self._close_btn.rect().bottomLeft())
        menu.exec(pos)

    def _toggle_maximize(self):
        if self._maximized:
            if self._normal_geo is not None:
                self.setGeometry(self._normal_geo)
            self._maximized = False
            self._max_btn.setText("□")
        else:
            self._normal_geo = self.geometry()
            screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
            self.setGeometry(screen.availableGeometry())
            self._maximized = True
            self._max_btn.setText("❐")

    def _show_cleanup(self):
        dialog = CleanupDialog(self)
        if dialog.exec():
            self.refresh()

    def _show_recycle_bin(self):
        dialog = RecycleBinDialog(self)
        dialog.items_changed.connect(self.refresh)
        dialog.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            if self._on_hidden:
                self._on_hidden()
        super().keyPressEvent(event)
