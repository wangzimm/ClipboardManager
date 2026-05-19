"""Settings dialog — retention time, auto-start."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QCheckBox,
)

from settings_manager import get_retention_hours, set_retention_hours, get_hours_options
from settings_manager import get_auto_start, set_auto_start


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(280, 170)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background-color: #E3F2FD; }
            QLabel { color: #424242; font-size: 13px; }
            QComboBox {
                border: 1px solid #BBDEFB; border-radius: 4px;
                padding: 4px 10px; background: #FFFFFF;
                color: #212121; font-size: 12px;
            }
            QCheckBox { color: #424242; font-size: 13px; }
            QPushButton#saveBtn {
                background-color: #64B5F6; color: #FFFFFF;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-size: 12px;
            }
            QPushButton#saveBtn:hover { background-color: #1E88E5; }
            QPushButton#cancelBtn {
                background-color: #E0E0E0; color: #424242;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-size: 12px;
            }
            QPushButton#cancelBtn:hover { background-color: #BDBDBD; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 18)

        self._options = get_hours_options()  # [(hours, label), ...]

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("保留时间："))
        self._retention = QComboBox()
        labels = [label for _, label in self._options]
        self._retention.addItems(labels)

        current_hours = get_retention_hours()
        idx = 0
        for i, (h, _) in enumerate(self._options):
            if h == current_hours:
                idx = i
                break
        self._retention.setCurrentIndex(idx)

        row1.addWidget(self._retention, stretch=1)
        layout.addLayout(row1)

        self._auto_start = QCheckBox("开机自动启动")
        self._auto_start.setChecked(get_auto_start())
        layout.addWidget(self._auto_start)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("cancelBtn")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        save = QPushButton("保存")
        save.setObjectName("saveBtn")
        save.clicked.connect(self._save)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _save(self):
        idx = self._retention.currentIndex()
        if 0 <= idx < len(self._options):
            set_retention_hours(self._options[idx][0])
        set_auto_start(self._auto_start.isChecked())
        self.accept()
