"""Recycle bin dialog — shows deleted items, restore / permanent-delete."""
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QSizePolicy, QMessageBox,
)

from database import get_recycle_items, restore_from_recycle, permanent_delete, empty_recycle, restore_all_recycle


STYLE = """
QDialog#recycleDialog {
    background-color: #E3F2FD;
    border: 1px solid #BBDEFB;
    border-radius: 8px;
}
"""

ITEM_STYLE = """
QFrame#recycleItem {
    background-color: #FFEBEE;
    border: 1px solid #FFCDD2;
    border-radius: 4px;
}
QFrame#recycleItem:hover {
    background-color: #FFCDD2;
}
"""


class RecycleBinDialog(QDialog):
    items_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self.setObjectName("recycleDialog")
        self.setWindowTitle("回收站")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumSize(320, 300)
        self.resize(360, 420)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("回收站")
        title.setStyleSheet("color: #424242; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("删除的内容保留 7 天，到期自动清除")
        hint.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Scroll area for items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._item_container = QWidget()
        self._item_layout = QVBoxLayout(self._item_container)
        self._item_layout.setContentsMargins(0, 0, 0, 0)
        self._item_layout.setSpacing(6)
        self._item_layout.addStretch()
        scroll.setWidget(self._item_container)
        layout.addWidget(scroll, stretch=1)

        # Bottom buttons
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self._count_label = QLabel()
        self._count_label.setStyleSheet("color: #757575; font-size: 11px;")
        bottom.addWidget(self._count_label)
        bottom.addStretch()

        restore_all_btn = QPushButton("恢复全部")
        restore_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_all_btn.setStyleSheet("""
            QPushButton {
                background: #C8E6C9; border: 1px solid #A5D6A7;
                border-radius: 4px; padding: 6px 14px; color: #2E7D32;
                font-size: 12px;
            }
            QPushButton:hover { background: #A5D6A7; }
        """)
        restore_all_btn.clicked.connect(self._restore_all)
        bottom.addWidget(restore_all_btn)

        empty_btn = QPushButton("清空回收站")
        empty_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_btn.setStyleSheet("""
            QPushButton {
                background: #FFCDD2; border: 1px solid #EF9A9A;
                border-radius: 4px; padding: 6px 14px; color: #C62828;
                font-size: 12px;
            }
            QPushButton:hover { background: #EF9A9A; }
        """)
        empty_btn.clicked.connect(self._empty_all)
        bottom.addWidget(empty_btn)

        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #E3F2FD; border: 1px solid #90CAF9;
                border-radius: 4px; padding: 6px 14px; color: #1565C0;
                font-size: 12px;
            }
            QPushButton:hover { background: #BBDEFB; }
        """)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)

        layout.addLayout(bottom)
        self._load()

    def _load(self):
        # Clear existing items
        while self._item_layout.count() > 1:  # keep the stretch
            item = self._item_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        items = get_recycle_items()
        self._count_label.setText(f"共 {len(items)} 项")

        for row in items:
            self._add_item(row)

    def _add_item(self, row):
        item_id, item_type, content, pinned, created, deleted = row

        frame = QFrame()
        frame.setObjectName("recycleItem")
        frame.setStyleSheet(ITEM_STYLE)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        fl = QHBoxLayout(frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(8)

        # Content preview
        if item_type == "text" and content:
            display = content[:60].replace("\n", " ")
            if len(content) > 60:
                display += "..."
        else:
            display = "[图片]"

        info = QLabel(f"{display}\n删除于 {deleted or ''}")
        info.setStyleSheet("color: #424242; font-size: 11px;")
        info.setWordWrap(True)
        fl.addWidget(info, stretch=1)

        # Restore button
        restore_btn = QPushButton("恢复")
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_btn.setFixedSize(50, 26)
        restore_btn.setStyleSheet("""
            QPushButton {
                background: #C8E6C9; border: 1px solid #A5D6A7;
                border-radius: 3px; color: #2E7D32; font-size: 11px;
            }
            QPushButton:hover { background: #A5D6A7; }
        """)
        restore_btn.clicked.connect(lambda checked=False, iid=item_id: self._restore(iid))
        fl.addWidget(restore_btn)

        # Permanently delete button
        perm_btn = QPushButton("彻底删除")
        perm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        perm_btn.setFixedSize(60, 26)
        perm_btn.setStyleSheet("""
            QPushButton {
                background: #FFCDD2; border: 1px solid #EF9A9A;
                border-radius: 3px; color: #C62828; font-size: 11px;
            }
            QPushButton:hover { background: #EF9A9A; }
        """)
        perm_btn.clicked.connect(lambda checked=False, iid=item_id: self._perm_delete(iid))
        fl.addWidget(perm_btn)

        self._item_layout.insertWidget(self._item_layout.count() - 1, frame)

    def _restore(self, item_id):
        restore_from_recycle(item_id)
        self._load()
        self.items_changed.emit()

    def _restore_all(self):
        reply = QMessageBox.question(
            self, "确认恢复", "确定要恢复回收站中的所有项目吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            restore_all_recycle()
            self.items_changed.emit()
            self.accept()

    def _perm_delete(self, item_id):
        permanent_delete(item_id)
        self._load()
        self.items_changed.emit()

    def _empty_all(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空回收站吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            empty_recycle()
            self.items_changed.emit()
            self.accept()

    # ── drag ─────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
