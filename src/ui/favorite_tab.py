"""Favorites tab — shows both text and image items marked as favorite."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QMessageBox,
    QPushButton,
)

from database import get_favorites, toggle_favorite, delete_item
from ui.card_widget import CardWidget


TOOLBAR_STYLE = """
QPushButton {
    background: #E8F5E9;
    border: 1px solid #A5D6A7;
    border-radius: 3px;
    padding: 3px 10px;
    color: #2E7D32;
    font-size: 11px;
}
QPushButton:hover {
    background: #C8E6C9;
    border: 1px solid #66BB6A;
}
"""


class FavoriteTab(QWidget):
    copy_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loaded = False
        self._card_ids = set()
        self._selected_ids = {}
        self._cards = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)

        # Batch action bar
        self._batch_bar = self._create_batch_bar()
        self._batch_bar.setVisible(False)
        layout.addWidget(self._batch_bar)

        # Scroll area
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

        self._empty = QLabel("暂无收藏记录")
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

        layout.addStretch()
        return bar

    # ── batch bar ─────────────────────────────────────────────

    def _create_batch_bar(self):
        bar = QWidget()
        bar.setStyleSheet("""
            QWidget {
                background: #C8E6C9;
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        self._batch_count = QLabel("已选 0 项")
        self._batch_count.setStyleSheet("color: #2E7D32; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(self._batch_count)

        layout.addStretch()

        copy_btn = QPushButton("批量复制")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #E8F5E9; border: 1px solid #A5D6A7;
                border-radius: 3px; padding: 4px 12px;
                color: #2E7D32; font-size: 11px;
            }
            QPushButton:hover { background: #C8E6C9; }
        """)
        copy_btn.clicked.connect(self._batch_copy)
        layout.addWidget(copy_btn)

        pin_btn = QPushButton("批量置顶")
        pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pin_btn.setStyleSheet("""
            QPushButton {
                background: #FFFDE7; border: 1px solid #FFE082;
                border-radius: 3px; padding: 4px 12px;
                color: #F57F17; font-size: 11px;
            }
            QPushButton:hover { background: #FFF9C4; }
        """)
        pin_btn.clicked.connect(self._batch_pin)
        layout.addWidget(pin_btn)

        unfav_btn = QPushButton("取消收藏")
        unfav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        unfav_btn.setStyleSheet("""
            QPushButton {
                background: #FFF3E0; border: 1px solid #FFCC80;
                border-radius: 3px; padding: 4px 12px;
                color: #E65100; font-size: 11px;
            }
            QPushButton:hover { background: #FFE0B2; }
        """)
        unfav_btn.clicked.connect(self._batch_unfavorite)
        layout.addWidget(unfav_btn)

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

    def refresh(self):
        self._rebuild()

    def _connect_card(self, card):
        card.copy_triggered.connect(self.copy_triggered.emit)
        card.pin_toggled.connect(lambda cid: self._rebuild())
        card.favorite_toggled.connect(lambda cid: self._rebuild())
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

        items = get_favorites(limit=30, include_image_data=False)
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
            elif card and card.item_type == "image":
                card._copy_to_clipboard()
        if texts:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText("\n---\n".join(texts))
        self.copy_triggered.emit()
        self._clear_selection()

    def _batch_pin(self):
        if not self._selected_ids:
            return
        from database import toggle_pin
        for item_id in list(self._selected_ids):
            toggle_pin(item_id)
        self._selected_ids.clear()
        self._rebuild()

    def _batch_unfavorite(self):
        if not self._selected_ids:
            return
        count = len(self._selected_ids)
        reply = QMessageBox.question(
            self, "确认取消收藏", f"确定要取消收藏选中的 {count} 项吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for item_id in list(self._selected_ids):
                toggle_favorite(item_id)
            self._selected_ids.clear()
            self._rebuild()

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
            for item_id in list(self._selected_ids):
                delete_item(item_id)
            self._selected_ids.clear()
            self._rebuild()

    # ── single item operations ─────────────────────────────────

    def _on_delete(self, item_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条收藏记录吗？\n删除后可在回收站保留 7 天。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_item(item_id)
            self._rebuild()
