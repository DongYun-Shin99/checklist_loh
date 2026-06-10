"""체크리스트 상세 화면: 항목 체크, 경로 열기, 메모."""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..models import Checklist, ChecklistItem, STATUS_DONE, STATUS_IN_PROGRESS
from ..storage import Storage
from ..utils import dday_info, open_in_explorer
from .checklists import country_badge


class ItemRow(QFrame):
    statusChanged = Signal()

    def __init__(self, item: ChecklistItem, storage: Storage, read_only: bool = False):
        super().__init__()
        self.item = item
        self.storage = storage
        self.setProperty("card", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self.checkbox = QCheckBox(item.description)
        self.checkbox.setChecked(item.done)
        self.checkbox.setEnabled(not read_only)
        self.checkbox.toggled.connect(self._on_toggled)
        top.addWidget(self.checkbox, 1)
        self.status_label = QLabel()
        top.addWidget(self.status_label)
        layout.addLayout(top)

        if item.path:
            path_row = QHBoxLayout()
            path_row.setContentsMargins(26, 0, 0, 0)
            exists = os.path.exists(item.path)
            path_label = QLabel(f"📁 {item.path}" + ("" if exists else "   ⚠ 경로 없음"))
            path_label.setStyleSheet(
                "border: none; font-size: 12px; color: "
                + ("#6b7280" if exists else "#dc2626")
            )
            path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            path_row.addWidget(path_label, 1)
            open_btn = QPushButton("열기")
            open_btn.setProperty("small", True)
            open_btn.setEnabled(exists)
            open_btn.clicked.connect(lambda: open_in_explorer(item.path))
            path_row.addWidget(open_btn)
            layout.addLayout(path_row)

        memo_row = QHBoxLayout()
        memo_row.setContentsMargins(26, 0, 0, 0)
        self.memo_edit = QLineEdit(item.memo)
        self.memo_edit.setProperty("flat", True)
        self.memo_edit.setPlaceholderText("메모 추가...")
        self.memo_edit.setReadOnly(read_only)
        self.memo_edit.textEdited.connect(self._on_memo_edited)
        memo_row.addWidget(self.memo_edit)
        layout.addLayout(memo_row)

        self._apply_status_style()

    def _on_toggled(self, checked: bool) -> None:
        self.item.status = STATUS_DONE if checked else STATUS_IN_PROGRESS
        self.storage.save()
        self._apply_status_style()
        self.statusChanged.emit()

    def _on_memo_edited(self, text: str) -> None:
        self.item.memo = text
        self.storage.save()

    def _apply_status_style(self) -> None:
        if self.item.done:
            self.status_label.setText("완료 ✓")
            self.status_label.setStyleSheet(
                "border:none; color:#059669; font-weight:bold; font-size:12px;"
            )
            self.checkbox.setStyleSheet(
                "QCheckBox { color: #9ca3af; text-decoration: line-through; }"
            )
        else:
            self.status_label.setText("진행중")
            self.status_label.setStyleSheet(
                "border:none; color:#d97706; font-weight:bold; font-size:12px;"
            )
            self.checkbox.setStyleSheet("QCheckBox { color: #111827; }")


class ChecklistDetailPage(QWidget):
    backRequested = Signal()
    archivedChanged = Signal()

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.checklist: Checklist | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        back_btn = QPushButton("← 뒤로")
        back_btn.clicked.connect(self.backRequested.emit)
        header.addWidget(back_btn)
        self.title_label = QLabel()
        self.title_label.setProperty("h1", True)
        header.addWidget(self.title_label)
        self.badge_host = QHBoxLayout()
        header.addLayout(self.badge_host)
        header.addStretch()
        self.dday_label = QLabel()
        header.addWidget(self.dday_label)
        layout.addLayout(header)

        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        progress_row.addWidget(self.progress_bar, 1)
        self.progress_label = QLabel()
        self.progress_label.setProperty("muted", True)
        progress_row.addWidget(self.progress_label)
        self.sort_toggle = QCheckBox("완료 항목 아래로")
        self.sort_toggle.toggled.connect(self._rebuild_items)
        progress_row.addWidget(self.sort_toggle)
        layout.addLayout(progress_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.items_host = QWidget()
        self.items_layout = QVBoxLayout(self.items_host)
        self.items_layout.setContentsMargins(0, 0, 6, 0)
        self.items_layout.setSpacing(8)
        self.items_layout.addStretch()
        scroll.setWidget(self.items_host)
        layout.addWidget(scroll, 1)

    def set_checklist(self, checklist: Checklist) -> None:
        self.checklist = checklist
        self.refresh()

    def refresh(self) -> None:
        if not self.checklist:
            return
        c = self.checklist
        self.title_label.setText(c.name)

        while self.badge_host.count():
            item = self.badge_host.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.badge_host.addWidget(country_badge(c))

        dday_text, dday_color = dday_info(c.due_date)
        self.dday_label.setText(f"기한: {c.due_date or '없음'}  {dday_text}")
        self.dday_label.setStyleSheet(f"color: {dday_color}; font-weight: bold;")
        self._update_progress()
        self._rebuild_items()

    def _update_progress(self) -> None:
        done, total = self.checklist.progress
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(done)
        self.progress_label.setText(f"{done}/{total}")

    def _rebuild_items(self) -> None:
        while self.items_layout.count() > 1:
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = list(self.checklist.items)
        if self.sort_toggle.isChecked():
            items.sort(key=lambda i: i.done)  # 진행중 먼저, 원래 순서 유지(안정 정렬)
        for item in items:
            row = ItemRow(item, self.storage)
            row.statusChanged.connect(self._on_item_status_changed)
            self.items_layout.insertWidget(self.items_layout.count() - 1, row)

    def _on_item_status_changed(self) -> None:
        self._update_progress()
        done, total = self.checklist.progress
        if total and done == total and not self.checklist.is_archived:
            answer = QMessageBox.question(
                self,
                "모든 항목 완료",
                "모든 항목이 완료되었습니다.\n완료 처리하고 보관함으로 이동할까요?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.checklist.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.storage.save()
                self.archivedChanged.emit()
                self.backRequested.emit()
                return
        if self.sort_toggle.isChecked():
            self._rebuild_items()
