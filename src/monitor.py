from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication


class ClipboardMonitor(QObject):
    text_copied = Signal(str)
    image_copied = Signal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clipboard = QApplication.clipboard()
        self._last_text = ""
        self._last_image_key = 0
        self._skip_next = False

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._check)
        self._timer.start()

    def _check(self):
        if self._skip_next:
            self._skip_next = False
            return

        if self._clipboard.mimeData().hasImage():
            image = self._clipboard.image()
            if not image.isNull():
                key = image.cacheKey()
                if key != self._last_image_key:
                    self._last_image_key = key
                    from PySide6.QtCore import QByteArray, QBuffer, QIODevice
                    ba = QByteArray()
                    buf = QBuffer(ba)
                    buf.open(QIODevice.OpenModeFlag.WriteOnly)
                    image.save(buf, "PNG")
                    buf.close()
                    self.image_copied.emit(bytes(ba))
                return

        if self._clipboard.mimeData().hasText():
            text = self._clipboard.text()
            if text and text != self._last_text:
                self._last_text = text
                self.text_copied.emit(text)

    def mark_skip_next(self):
        self._skip_next = True
