"""Search bar widget — real-time filtering, green accent."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QLineEdit


class SearchBar(QLineEdit):
    search_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("搜索文字内容...")
        self.setClearButtonEnabled(True)
        self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #90CAF9;
                border-radius: 4px;
                padding: 6px 10px;
                background: #E3F2FD;
                color: #212121;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #42A5F5;
            }
        """)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(200)
        self._debounce.timeout.connect(self._emit_search)
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self):
        self._debounce.start()

    def _emit_search(self):
        self.search_changed.emit(self.text().strip())
