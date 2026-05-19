"""Cleanup dialog — choose time + direction, then delete items."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QMessageBox,
)

from database import cleanup_expired
from settings_manager import get_cleanup_hours_options


class CleanupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手动清理")
        self.setFixedSize(260, 190)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background-color: #E3F2FD; }
            QLabel { color: #424242; font-size: 13px; }
            QComboBox {
                border: 1px solid #BBDEFB; border-radius: 4px;
                padding: 4px 10px; background: #FFFFFF;
                color: #212121; font-size: 12px;
            }
            QPushButton#cleanBtn {
                background-color: #EF5350; color: #FFFFFF;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-size: 12px;
            }
            QPushButton#cleanBtn:hover { background-color: #C62828; }
            QPushButton#cancelBtn {
                background-color: #E0E0E0; color: #424242;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-size: 12px;
            }
            QPushButton#cancelBtn:hover { background-color: #BDBDBD; }
        """)

        self._options = get_cleanup_hours_options()
        self._newer = False  # default: older (早于)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 14)

        # Type picker
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("类型："))
        self._type_combo = QComboBox()
        self._type_combo.addItems(["全部", "文字", "图片"])
        row0.addWidget(self._type_combo, stretch=1)
        layout.addLayout(row0)

        # Time picker
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("时间："))
        self._time_combo = QComboBox()
        self._time_combo.addItems([label for _, label in self._options])
        self._time_combo.setCurrentIndex(0)  # default "1 小时"
        row1.addWidget(self._time_combo, stretch=1)
        layout.addLayout(row1)

        # Direction toggle
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("范围："))
        self._dir_btn = QPushButton("早于")
        self._dir_btn.setFixedWidth(60)
        self._dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dir_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #BBDEFB; border-radius: 4px;
                padding: 4px 8px; background: #FFFFFF;
                color: #212121; font-size: 12px;
            }
        """)
        self._dir_btn.clicked.connect(self._toggle_dir)
        row2.addWidget(self._dir_btn)
        hint = QLabel("删除所选时间之外的记录")
        hint.setStyleSheet("color: #9E9E9E; font-size: 10px;")
        row2.addWidget(hint)
        row2.addStretch()
        layout.addLayout(row2)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("cancelBtn")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        clean = QPushButton("清理")
        clean.setObjectName("cleanBtn")
        clean.clicked.connect(self._do_clean)
        btn_row.addWidget(clean)
        layout.addLayout(btn_row)

    def _toggle_dir(self):
        self._newer = not self._newer
        self._dir_btn.setText("晚于" if self._newer else "早于")

    def _do_clean(self):
        idx = self._time_combo.currentIndex()
        if idx < 0 or idx >= len(self._options):
            return
        hours = self._options[idx][0]
        direction = "newer" if self._newer else "older"
        dir_text = "晚于" if self._newer else "早于"
        label = self._options[idx][1]

        type_map = {0: None, 1: "text", 2: "image"}
        item_type = type_map[self._type_combo.currentIndex()]
        type_text = ["全部", "文字", "图片"][self._type_combo.currentIndex()]

        reply = QMessageBox.question(
            self, "确认清理",
            f"确定要删除 {type_text} 中 {dir_text} {label} 的记录吗？\n置顶项不受影响。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted = cleanup_expired(hours, direction, item_type)
            QMessageBox.information(
                self, "完成", f"已清理 {deleted} 条记录。"
            )
            self.accept()
