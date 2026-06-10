"""진행 중인 체크리스트 목록 화면 (메인)."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..dialogs import NewChecklistDialog
from ..models import COUNTRY_COLORS, Checklist, create_checklist_from_preset
from ..storage import Storage
from ..utils import dday_info


def country_badge(checklist: Checklist) -> QLabel:
    badge = QLabel(checklist.country_name)
    color = COUNTRY_COLORS.get(checklist.country, "#6b7280")
    badge.setStyleSheet(
        f"background: {color}; color: white; border-radius: 9px;"
        "padding: 2px 10px; font-size: 12px; font-weight: bold;"
    )
    return badge


class ChecklistCard(QFrame):
    clicked = Signal(str)
    menuRequested = Signal(str, object)  # id, global pos

    def __init__(self, checklist: Checklist):
        super().__init__()
        self.checklist_id = checklist.id
        self.setProperty("card", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        name = QLabel(checklist.name)
        name.setStyleSheet("font-size: 15px; font-weight: bold; border: none;")
        top.addWidget(name)
        top.addWidget(country_badge(checklist))
        top.addStretch()
        dday_text, dday_color = dday_info(checklist.due_date)
        dday = QLabel(dday_text)
        dday.setStyleSheet(f"color: {dday_color}; font-weight: bold; border: none;")
        top.addWidget(dday)
        layout.addLayout(top)

        done, total = checklist.progress
        bottom = QHBoxLayout()
        bar = QProgressBar()
        bar.setMaximum(max(total, 1))
        bar.setValue(done)
        bar.setTextVisible(False)
        bottom.addWidget(bar, 1)
        count = QLabel(f"{done}/{total}")
        count.setStyleSheet("color: #6b7280; border: none;")
        bottom.addWidget(count)
        layout.addLayout(bottom)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.checklist_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.menuRequested.emit(self.checklist_id, event.globalPos())


class ChecklistListPage(QWidget):
    openRequested = Signal(str)  # checklist id
    dataChanged = Signal()

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("진행 중인 체크리스트")
        title.setProperty("h1", True)
        header.addWidget(title)
        header.addStretch()
        new_btn = QPushButton("＋ 새 체크리스트")
        new_btn.setProperty("primary", True)
        new_btn.clicked.connect(self._create_checklist)
        header.addWidget(new_btn)
        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_host)
        layout.addWidget(self.scroll, 1)

        self.empty_label = QLabel(
            "진행 중인 체크리스트가 없습니다.\n[＋ 새 체크리스트]를 눌러 프리셋에서 만들어보세요."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active = self.storage.active_checklists()
        self.empty_label.setVisible(not active)
        self.scroll.setVisible(bool(active))

        def sort_key(c: Checklist):
            try:
                return (0, date.fromisoformat(c.due_date))
            except ValueError:
                return (1, date.max)

        for checklist in sorted(active, key=sort_key):
            card = ChecklistCard(checklist)
            card.clicked.connect(self.openRequested.emit)
            card.menuRequested.connect(self._show_card_menu)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    # ---- 동작 ----
    def _create_checklist(self) -> None:
        if not self.storage.presets:
            QMessageBox.information(
                self, "프리셋 없음",
                "체크리스트를 만들려면 먼저 프리셋이 필요합니다.\n프리셋 메뉴에서 만들어주세요.",
            )
            return
        dialog = NewChecklistDialog(self.storage.presets, self)
        if dialog.exec():
            preset, country, name, due = dialog.result_values()
            checklist = create_checklist_from_preset(
                preset, country, name, due,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            self.storage.checklists.append(checklist)
            self.storage.save()
            self.refresh()
            self.openRequested.emit(checklist.id)

    def _show_card_menu(self, checklist_id: str, global_pos) -> None:
        checklist = self.storage.find_checklist(checklist_id)
        if not checklist:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("이름 변경")
        due_action = menu.addAction("기한 변경")
        done, total = checklist.progress
        archive_action = None
        if total and done == total:
            archive_action = menu.addAction("보관함으로 이동")
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == rename_action:
            text, ok = QInputDialog.getText(self, "이름 변경", "새 이름:", text=checklist.name)
            if ok and text.strip():
                checklist.name = text.strip()
        elif chosen == due_action:
            text, ok = QInputDialog.getText(
                self, "기한 변경", "기한 (YYYY-MM-DD):", text=checklist.due_date
            )
            if ok:
                try:
                    date.fromisoformat(text.strip())
                    checklist.due_date = text.strip()
                except ValueError:
                    QMessageBox.warning(self, "형식 오류", "YYYY-MM-DD 형식으로 입력해주세요.")
        elif archive_action and chosen == archive_action:
            checklist.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.dataChanged.emit()
        elif chosen == delete_action:
            answer = QMessageBox.question(
                self, "삭제", f'"{checklist.name}" 체크리스트를 삭제할까요?'
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.storage.checklists.remove(checklist)
        self.storage.save()
        self.refresh()
