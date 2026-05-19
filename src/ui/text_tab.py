"""Text clipboard tab — scrollable list of text cards with search and batch ops."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QMessageBox,
    QPushButton,
)

from database import get_items
from ui.card_widget import CardWidget


TOOLBAR_STYLE = """
QPushButton {
    background: #E3F2FD;
    border: 1px solid #90CAF9;
    border-radius: 3px;
    padding: 3px 10px;
    color: #1565C0;
    font-size: 11px;
}
QPushButton:hover {
    background: #BBDEFB;
    border: 1px solid #42A5F5;
}
"""


class TextTab(QWidget):
    copy_triggered = Signal()
    favorites_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search = None
        self._loaded = False
        self._card_ids = set()
        self._selected_ids = {}
        self._cards = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar — always visible
        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)

        # Batch action bar (visible when items are selected)
        self._batch_bar = self._create_batch_bar()
        self._batch_bar.setVisible(False)
        layout.addWidget(self._batch_bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #E3F2FD; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: #E3F2FD;")
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setContentsMargins(4, 4, 4, 4)
        self._card_layout.setSpacing(6)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        self._empty = QLabel("暂无文字记录")
        self._empty.setStyleSheet("color: #9E9E9E; font-size: 13px; padding: 30px;")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)

    # ── toolbar ───────────────────────────────────────────────

    def _create_toolbar(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(6)

        self._select_all_btn = QPushButton("全选")
        self._select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_btn.setStyleSheet(TOOLBAR_STYLE)
        self._select_all_btn.clicked.connect(self._select_all)
        layout.addWidget(self._select_all_btn)

        layout.addSpacing(6)

        del_1h = QPushButton("删除 >1小时")
        del_1h.setCursor(Qt.CursorShape.PointingHandCursor)
        del_1h.setStyleSheet(TOOLBAR_STYLE)
        del_1h.clicked.connect(lambda: self._delete_older_than(1, "1 小时"))
        layout.addWidget(del_1h)

        del_1d = QPushButton("删除 >1天")
        del_1d.setCursor(Qt.CursorShape.PointingHandCursor)
        del_1d.setStyleSheet(TOOLBAR_STYLE)
        del_1d.clicked.connect(lambda: self._delete_older_than(24, "1 天"))
        layout.addWidget(del_1d)

        del_3d = QPushButton("删除 >3天")
        del_3d.setCursor(Qt.CursorShape.PointingHandCursor)
        del_3d.setStyleSheet(TOOLBAR_STYLE)
        del_3d.clicked.connect(lambda: self._delete_older_than(72, "3 天"))
        layout.addWidget(del_3d)

        layout.addStretch()
        return bar

    # ── batch bar ─────────────────────────────────────────────

    def _create_batch_bar(self):
        bar = QWidget()
        bar.setStyleSheet("""
            QWidget {
                background: #BBDEFB;
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        self._batch_count = QLabel("已选 0 项")
        self._batch_count.setStyleSheet("color: #1565C0; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(self._batch_count)

        layout.addStretch()

        copy_btn = QPushButton("批量复制")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #E3F2FD; border: 1px solid #90CAF9;
                border-radius: 3px; padding: 4px 12px;
                color: #1565C0; font-size: 11px;
            }
            QPushButton:hover { background: #BBDEFB; }
        """)
        copy_btn.clicked.connect(self._batch_copy)
        layout.addWidget(copy_btn)

        del_btn = QPushButton("批量删除")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background: #FFEBEE; border: 1px solid #FFCDD2;
                border-radius: 3px; padding: 4px 12px;
                color: #C62828; font-size: 11px;
            }
            QPushButton:hover { background: #FFCDD2; }
        """)
        del_btn.clicked.connect(self._batch_delete)
        layout.addWidget(del_btn)

        clear_btn = QPushButton("取消选择")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #757575; font-size: 11px;
            }
            QPushButton:hover { color: #424242; text-decoration: underline; }
        """)
        clear_btn.clicked.connect(self._clear_selection)
        layout.addWidget(clear_btn)

        return bar

    # ── public API ────────────────────────────────────────────

    def set_search(self, keyword):
        self._search = keyword if keyword else None
        self._rebuild()

    def refresh(self):
        self._rebuild()

    def add_card(self, item_data):
        item_id = item_data[0]
        if item_id in self._card_ids:
            old = self._cards.get(item_id)
            if old:
                self._card_layout.removeWidget(old)
                old.deleteLater()
            self._card_ids.discard(item_id)
        self._card_ids.add(item_id)
        self._empty.setVisible(False)
        card = CardWidget(item_data)
        self._connect_card(card)
        self._card_layout.insertWidget(self._card_layout.count() - 1, card)
        self._cards[item_id] = card

    def _connect_card(self, card):
        card.copy_triggered.connect(self.copy_triggered.emit)
        card.pin_toggled.connect(lambda cid: self._on_pin(cid))
        card.favorite_toggled.connect(lambda cid: self._on_favorite_toggled(cid))
        card.delete_requested.connect(lambda cid: self._on_delete(cid))
        card.selection_toggled.connect(self._on_selection_changed)

    def _rebuild(self):
        self._card_ids.clear()
        self._selected_ids.clear()
        self._cards.clear()
        while self._card_layout.count() > 1:
            item = self._card_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._empty:
                w.deleteLater()
        self._batch_bar.setVisible(False)

        items = get_items(item_type="text", search=self._search, include_image_data=False)
        self._loaded = True
        if not items:
            self._empty.setVisible(True)
            self._card_layout.insertWidget(0, self._empty)
            return

        self._empty.setVisible(False)
        for item_data in items:
            self._card_ids.add(item_data[0])
            card = CardWidget(item_data)
            self._connect_card(card)
            self._cards[item_data[0]] = card
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)

    # ── selection ─────────────────────────────────────────────

    def _select_all(self):
        all_selected = len(self._selected_ids) == len(self._cards)
        if all_selected:
            self._clear_selection()
            self._select_all_btn.setText("全选")
        else:
            for card in self._cards.values():
                card.set_selected(True)
                self._selected_ids[card.item_id] = True
            count = len(self._selected_ids)
            self._batch_count.setText(f"已选 {count} 项")
            self._batch_bar.setVisible(count > 0)
            self._select_all_btn.setText("取消全选")

    def _on_selection_changed(self, item_id, selected):
        if selected:
            self._selected_ids[item_id] = True
        else:
            self._selected_ids.pop(item_id, None)
        count = len(self._selected_ids)
        self._batch_count.setText(f"已选 {count} 项")
        self._batch_bar.setVisible(count > 0)
        self._select_all_btn.setText("全选" if count < len(self._cards) else "取消全选")

    def _clear_selection(self):
        for item_id in list(self._selected_ids):
            card = self._cards.get(item_id)
            if card:
                card.set_selected(False)
        self._selected_ids.clear()
        self._batch_bar.setVisible(False)
        self._select_all_btn.setText("全选")

    def _batch_copy(self):
        if not self._selected_ids:
            return
        texts = []
        for item_id in self._selected_ids:
            card = self._cards.get(item_id)
            if card and card.item_type == "text":
                texts.append(card._content)
        if texts:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText("\n---\n".join(texts))
        self.copy_triggered.emit()
        self._clear_selection()

    def _batch_delete(self):
        if not self._selected_ids:
            return
        count = len(self._selected_ids)
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除选中的 {count} 条记录吗？\n删除后可在回收站保留 7 天。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from database import delete_item
            for item_id in list(self._selected_ids):
                delete_item(item_id)
            self._selected_ids.clear()
            self._rebuild()

    # ── time-based delete ─────────────────────────────────────

    def _delete_older_than(self, hours, label):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 {label} 之前的所有文字记录吗？\n（置顶项不会删除）\n删除后可在回收站保留 7 天。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from database import delete_items_older_than
            deleted = delete_items_older_than(hours, item_type="text")
            if deleted > 0:
                self._rebuild()

    # ── single item operations ─────────────────────────────────

    def _on_pin(self, item_id):
        from database import toggle_pin
        toggle_pin(item_id)
        self._rebuild()

    def _on_favorite_toggled(self, item_id):
        self._rebuild()
        self.favorites_changed.emit()

    def _on_delete(self, item_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条记录吗？\n删除后可在回收站保留 7 天。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from database import delete_item
            delete_item(item_id)
            self._rebuild()
