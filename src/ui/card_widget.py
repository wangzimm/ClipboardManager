"""Content card — click to reveal copy / delete actions, top-left select box."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QSizePolicy, QPushButton,
    QWidget,
)


CARD_STYLE = """
QFrame#card {
    background-color: #FFEBEE;
    border: 1px solid #FFCDD2;
    border-radius: 6px;
}
QFrame#card:hover {
    border: 1px solid #EF9A9A;
    background-color: #FFCDD2;
}
QFrame#card[clicked="true"] {
    background-color: #EF9A9A;
    border: 1px solid #E57373;
}
QFrame#card[selected="true"] {
    border: 2px solid #42A5F5;
}
QFrame#cardPinned {
    background-color: #FFFDE7;
    border: 1px solid #FFE082;
    border-radius: 6px;
}
QFrame#cardPinned:hover {
    border: 1px solid #FFA726;
    background-color: #FFF9C4;
}
QFrame#cardPinned[clicked="true"] {
    background-color: #FFE082;
    border: 1px solid #FFA726;
}
QFrame#cardPinned[selected="true"] {
    border: 2px solid #42A5F5;
}
QFrame#cardFavorite {
    background-color: #E8F5E9;
    border: 1px solid #A5D6A7;
    border-radius: 6px;
}
QFrame#cardFavorite:hover {
    border: 1px solid #81C784;
    background-color: #C8E6C9;
}
QFrame#cardFavorite[clicked="true"] {
    background-color: #A5D6A7;
    border: 1px solid #66BB6A;
}
QFrame#cardFavorite[selected="true"] {
    border: 2px solid #42A5F5;
}
"""

BTN_COPY_STYLE = """
QPushButton {
    background: #E3F2FD;
    border: 1px solid #90CAF9;
    border-radius: 4px;
    padding: 8px 12px;
    color: #1565C0;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background: #BBDEFB;
    border: 1px solid #42A5F5;
}
"""

BTN_DEL_STYLE = """
QPushButton {
    background: #FFEBEE;
    border: 1px solid #FFCDD2;
    border-radius: 4px;
    padding: 8px 12px;
    color: #C62828;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background: #FFCDD2;
    border: 1px solid #EF5350;
}
"""

SELECT_BTN_STYLE = """
QPushButton {
    border: none;
    background: transparent;
    color: #1E88E5;
    font-size: 18px;
    padding: 0px;
}
QPushButton:hover {
    color: #0D47A1;
}
"""

FAV_BTN_STYLE = """
QPushButton {
    border: none;
    background: transparent;
    color: #FFA726;
    font-size: 16px;
    padding: 0px;
}
QPushButton:hover {
    color: #F57C00;
}
"""


class CardWidget(QFrame):
    copy_triggered = Signal()
    pin_toggled = Signal(int)
    favorite_toggled = Signal(int)
    delete_requested = Signal(int)
    selection_toggled = Signal(int, bool)  # item_id, selected

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self._id = item_data[0]
        self._type = item_data[1]
        self._content = item_data[2]
        self._pinned = bool(item_data[4])
        self._created_at = item_data[5]
        self._favorite = bool(item_data[6]) if len(item_data) > 6 else False
        self._action_mode = False
        self._selected = False

        self._update_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Lazy-load image data if this is an image card without preloaded data
        image_data = item_data[3]
        if self._type == "image" and not image_data:
            from database import get_image_data
            image_data = get_image_data(self._id)

        self._normal_pixmap = None
        self._normal_view = self._create_normal_view(image_data)
        self._action_view = None  # lazy — only created on first click

        root.addWidget(self._normal_view)

    # ── style ─────────────────────────────────────────────────

    def _update_style(self):
        self.setProperty("clicked", False)
        self.setProperty("selected", self._selected)
        if self._pinned:
            self.setObjectName("cardPinned")
        elif self._favorite:
            self.setObjectName("cardFavorite")
        else:
            self.setObjectName("card")
        self.style().unpolish(self)
        self.style().polish(self)

    def _flash(self):
        self.setProperty("clicked", True)
        self.style().unpolish(self)
        self.style().polish(self)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._update_style)

    # ── selection ─────────────────────────────────────────────

    def _toggle_selection(self):
        self._selected = not self._selected
        marker = "●" if self._selected else "○"
        self._select_btn_normal.setText(marker)
        if hasattr(self, '_select_btn_action') and self._select_btn_action is not None:
            self._select_btn_action.setText(marker)
        self._update_style()
        self.selection_toggled.emit(self._id, self._selected)

    def _toggle_favorite(self):
        self._favorite = not self._favorite
        from database import toggle_favorite
        toggle_favorite(self._id)
        fav_marker = "★" if self._favorite else "☆"
        self._fav_btn_normal.setText(fav_marker)
        if hasattr(self, '_fav_btn_action') and self._fav_btn_action is not None:
            self._fav_btn_action.setText(fav_marker)
        self._update_style()
        self.favorite_toggled.emit(self._id)

    def set_selected(self, selected):
        self._selected = selected
        marker = "●" if self._selected else "○"
        self._select_btn_normal.setText(marker)
        if hasattr(self, '_select_btn_action') and self._select_btn_action is not None:
            self._select_btn_action.setText(marker)
        self._update_style()

    # ── normal view ───────────────────────────────────────────

    def _create_normal_view(self, image_data):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)

        # Selection toggle
        self._select_btn_normal = QPushButton("○")
        self._select_btn_normal.setFixedSize(20, 20)
        self._select_btn_normal.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_btn_normal.setStyleSheet(SELECT_BTN_STYLE)
        self._select_btn_normal.clicked.connect(self._toggle_selection)
        top.addWidget(self._select_btn_normal)

        # Favorite toggle
        fav_marker = "★" if self._favorite else "☆"
        self._fav_btn_normal = QPushButton(fav_marker)
        self._fav_btn_normal.setFixedSize(20, 20)
        self._fav_btn_normal.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn_normal.setStyleSheet(FAV_BTN_STYLE)
        self._fav_btn_normal.clicked.connect(self._toggle_favorite)
        top.addWidget(self._fav_btn_normal)

        if self._pinned:
            pin = QLabel("⬑")
            pin.setStyleSheet("color: #FFA726; font-size: 14px;")
            pin.setFixedWidth(16)
            top.addWidget(pin)

        if self._type == "image":
            thumb = QLabel()
            pix = QPixmap()
            if image_data:
                pix.loadFromData(image_data)
            if not pix.isNull():
                if pix.width() > 200:
                    pix = pix.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
                if pix.height() > 80:
                    pix = pix.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            else:
                pix = QPixmap(200, 40)
                pix.fill(QColor("#EEEEEE"))
                p = QPainter(pix)
                p.setPen(QColor("#BDBDBD"))
                p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "图片加载失败")
                p.end()
            self._normal_pixmap = pix
            thumb.setPixmap(pix)
            thumb.setScaledContents(True)
            thumb.setMaximumHeight(80)
            thumb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            top.addWidget(thumb, stretch=1)
        else:
            preview = QLabel()
            preview.setWordWrap(True)
            text = self._content or ""
            display = text[:200].replace("\n", " ")
            if len(text) > 200:
                display += "..."
            preview.setText(display)
            preview.setStyleSheet("color: #212121; font-size: 12px;")
            preview.setMaximumHeight(55)
            top.addWidget(preview, stretch=1)

        layout.addLayout(top)
        ts = QLabel(self._created_at or "")
        ts.setStyleSheet("color: #9E9E9E; font-size: 10px;")
        layout.addWidget(ts)
        return w

    # ── action view ───────────────────────────────────────────

    def _create_action_view(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(10, 8, 6, 6)
        root.setSpacing(6)

        # Top row: select + fav + content
        top = QHBoxLayout()
        top.setSpacing(8)

        self._select_btn_action = QPushButton("○")
        self._select_btn_action.setFixedSize(20, 20)
        self._select_btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_btn_action.setStyleSheet(SELECT_BTN_STYLE)
        self._select_btn_action.clicked.connect(self._toggle_selection)
        top.addWidget(self._select_btn_action)

        fav_marker = "★" if self._favorite else "☆"
        self._fav_btn_action = QPushButton(fav_marker)
        self._fav_btn_action.setFixedSize(20, 20)
        self._fav_btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn_action.setStyleSheet(FAV_BTN_STYLE)
        self._fav_btn_action.clicked.connect(self._toggle_favorite)
        top.addWidget(self._fav_btn_action)

        if self._pinned:
            pin = QLabel("⬑")
            pin.setStyleSheet("color: #FFA726; font-size: 12px;")
            top.addWidget(pin)

        if self._type == "image":
            thumb = QLabel()
            if self._normal_pixmap and not self._normal_pixmap.isNull():
                pix = QPixmap(self._normal_pixmap)
            else:
                pix = QPixmap(200, 40)
                pix.fill(QColor("#EEEEEE"))
                p = QPainter(pix)
                p.setPen(QColor("#BDBDBD"))
                p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "图片加载失败")
                p.end()
            thumb.setPixmap(pix)
            thumb.setScaledContents(True)
            thumb.setMaximumHeight(80)
            thumb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            top.addWidget(thumb, stretch=1)
        else:
            preview = QLabel()
            preview.setWordWrap(True)
            text = self._content or ""
            display = text[:100].replace("\n", " ")
            if len(text) > 100:
                display += "..."
            preview.setText(display)
            preview.setStyleSheet("color: #212121; font-size: 12px;")
            preview.setMaximumHeight(55)
            top.addWidget(preview, stretch=1)

        root.addLayout(top)

        ts = QLabel(self._created_at or "")
        ts.setStyleSheet("color: #9E9E9E; font-size: 9px;")
        root.addWidget(ts)

        # Bottom row: action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        copy_btn = QPushButton("复制")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(BTN_COPY_STYLE)
        copy_btn.clicked.connect(self._on_copy_clicked)
        btn_layout.addWidget(copy_btn)

        del_btn = QPushButton("删除")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(BTN_DEL_STYLE)
        del_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(del_btn)

        root.addLayout(btn_layout)
        return w

    # ── button callbacks ──────────────────────────────────────

    def _on_copy_clicked(self):
        self._copy_to_clipboard()
        self.copy_triggered.emit()
        self._flash()
        self._destroy_action_view()

    def _on_delete_clicked(self):
        self.delete_requested.emit(self._id)
        self._flash()

    # ── mouse ─────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child and isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return
            if self._action_mode:
                self._destroy_action_view()
            else:
                if self._action_view is None:
                    self._action_view = self._create_action_view()
                    self.layout().addWidget(self._action_view)
                self._normal_view.setVisible(False)
                self._action_view.setVisible(True)
                self._action_mode = True
        super().mousePressEvent(event)

    def _destroy_action_view(self):
        """Remove and delete the action view widget to free memory."""
        self._normal_view.setVisible(True)
        if self._action_view is not None:
            self._action_view.setVisible(False)
            self.layout().removeWidget(self._action_view)
            self._action_view.deleteLater()
            self._action_view = None
        self._action_mode = False
        self._select_btn_action = None
        self._fav_btn_action = None

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 0; }
            QMenu::item { padding: 6px 24px; color: #424242; font-size: 12px; }
            QMenu::item:selected { background-color: #E3F2FD; }
        """)
        pin_text = "取消置顶" if self._pinned else "置顶"
        pin_action = QAction(pin_text, None)
        pin_action.triggered.connect(lambda: self.pin_toggled.emit(self._id))
        menu.addAction(pin_action)
        fav_text = "取消收藏" if self._favorite else "收藏"
        fav_action = QAction(fav_text, None)
        fav_action.triggered.connect(self._toggle_favorite)
        menu.addAction(fav_action)
        del_action = QAction("删除", None)
        del_action.triggered.connect(lambda: self.delete_requested.emit(self._id))
        menu.addAction(del_action)
        menu.exec(event.globalPos())

    # ── clipboard ─────────────────────────────────────────────

    def _copy_to_clipboard(self):
        cb = QApplication.clipboard()
        if self._type == "text":
            cb.setText(self._content)
        elif self._type == "image":
            from database import get_image_data
            data = get_image_data(self._id)
            if data:
                img = QImage()
                img.loadFromData(data)
                cb.setImage(img)

    # ── properties ────────────────────────────────────────────

    @property
    def item_id(self):
        return self._id

    @property
    def item_type(self):
        return self._type
