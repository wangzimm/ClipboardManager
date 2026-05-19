"""Edge dock — full icon that auto-collapses to a thin strip after 2.5s idle."""
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QRectF, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QMouseEvent
from PySide6.QtWidgets import QWidget, QApplication

FULL_SIZE = 48
STRIP_W = 8
STRIP_H = 56
RADIUS = 14
STRIP_RADIUS = 6
BG_COLOR = QColor("#E3F2FD")
BORDER_COLOR = QColor("#90CAF9")
STRIP_COLOR = QColor("#90CAF9")
STRIP_HOVER_COLOR = QColor("#42A5F5")
ICON_COLOR = QColor("#42A5F5")
AUTO_COLLAPSE_MS = 2500


class DockWidget(QWidget):
    """Floating dock at the right screen edge.

    Shows as a 48×48 rounded square. After 2.5s without mouse hover,
    collapses into a thin 8px strip. Hovering the strip restores the
    full icon. Click the full icon to restore the main panel.
    """

    restore_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(None)
        self._drag_offset = None
        self._press_global = None
        self._hovered = False
        self._collapsed = False
        self._screen_right = 0

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._collapse)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

    # ── public API ─────────────────────────────────────────────

    def place_at(self, anchor_y: int):
        """Position the dock at the right screen edge near anchor_y."""
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self._screen_right = geo.right()
        y = anchor_y - FULL_SIZE // 2
        y = max(geo.top() + 4, min(y, geo.bottom() - FULL_SIZE - 4))

        self._collapsed = False
        self.setFixedSize(FULL_SIZE, FULL_SIZE)
        x = self._screen_right - FULL_SIZE
        self.move(QPoint(x, y))
        self.show()
        self._start_timer()

    # ── size states ────────────────────────────────────────────

    def _start_timer(self):
        self._collapse_timer.stop()
        if not self._hovered:
            self._collapse_timer.start(AUTO_COLLAPSE_MS)

    def _expand(self):
        """Restore full icon size."""
        if not self._collapsed:
            return
        self._collapsed = False
        self.setFixedSize(FULL_SIZE, FULL_SIZE)
        cur = self.geometry()
        x = self._screen_right - FULL_SIZE
        self.move(QPoint(x, cur.y()))
        self.update()

    def _collapse(self):
        """Shrink to thin strip."""
        if self._hovered or self._collapsed:
            return
        self._collapsed = True
        self.setFixedSize(STRIP_W, STRIP_H)
        cur = self.geometry()
        x = self._screen_right - STRIP_W
        self.move(QPoint(x, cur.y()))
        self.update()

    # ── paint ──────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._collapsed:
            self._draw_strip(p)
        else:
            self._draw_icon(p)
        p.end()

    def _draw_strip(self, p):
        color = STRIP_HOVER_COLOR if self._hovered else STRIP_COLOR
        r = QRectF(0, 2, STRIP_W + STRIP_RADIUS, STRIP_H - 4)
        path = QPainterPath()
        path.addRoundedRect(r, STRIP_RADIUS, STRIP_RADIUS)
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        p.setPen(QColor("#FFFFFF"))
        p.setBrush(QColor("#FFFFFF"))
        cx = STRIP_W // 2 + 1
        for dy in (-8, 0, 8):
            p.drawEllipse(QPoint(cx, STRIP_H // 2 + dy), 1.2, 1.2)

    def _draw_icon(self, p):
        r = QRect(2, 2, FULL_SIZE - 4, FULL_SIZE - 4)
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), RADIUS, RADIUS)

        p.setBrush(BG_COLOR)
        p.setPen(QPen(BORDER_COLOR, 2))
        p.drawPath(path)

        font = QFont("Segoe UI", 18)
        p.setFont(font)
        p.setPen(ICON_COLOR)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, "\U0001F4CB")

    # ── mouse events ───────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._collapsed:
                self._expand()
                self._start_timer()
                event.accept()
                return
            self._press_global = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_offset is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            screen = QApplication.primaryScreen()
            geo = screen.availableGeometry()
            self._screen_right = geo.right()
            x = self._screen_right - FULL_SIZE
            y = max(geo.top() + 4, min(new_pos.y(), geo.bottom() - FULL_SIZE - 4))
            self.move(QPoint(x, y))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_offset is not None:
            delta = 0
            if self._press_global is not None:
                delta = (event.globalPosition().toPoint() - self._press_global).manhattanLength()
            if delta < 5:
                self.hide()
                self.restore_requested.emit()
            self._drag_offset = None
            self._press_global = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._collapse_timer.stop()
        if self._collapsed:
            self._expand()
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self._start_timer()
        self.update()
