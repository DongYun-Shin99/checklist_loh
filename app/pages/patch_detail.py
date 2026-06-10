"""패치 상세 화면: 패치 안의 체크리스트 목록."""
from __future__ import annotations

from datetime import datetime

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

from ..dialogs import AddChecklistDialog
from ..models import Checklist, Patch, create_checklist_from_preset
from ..storage import Storage
from ..utils import dday_info
from ..widgets import country_badge


class ChecklistCard(QFrame):
    clicked = Signal(str)
    menuRequested = Signal(str, object)

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
        if checklist.is_done:
            done_mark = QLabel("완료 ✓")
            done_mark.setStyleSheet("color: #059669; font-weight: bold; border: none;")
            top.addWidget(done_mark)
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


class PatchDetailPage(QWidget):
    backRequested = Signal()
    openChecklistRequested = Signal(str)  # checklist id
    archivedChanged = Signal()

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.patch: Patch | None = None

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
        header.addStretch()
        self.due_label = QLabel()
        header.addWidget(self.due_label)
        add_btn = QPushButton("＋ 체크리스트 추가")
        add_btn.setProperty("primary", True)
        add_btn.clicked.connect(self._add_checklist)
        header.addWidget(add_btn)
        layout.addLayout(header)

        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        progress_row.addWidget(self.progress_bar, 1)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color: #2563eb; font-weight: bold;")
        progress_row.addWidget(self.progress_label)
        layout.addLayout(progress_row)

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
            "아직 체크리스트가 없습니다.\n[＋ 체크리스트 추가]로 프리셋과 국가를 골라 추가하세요."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def set_patch(self, patch: Patch) -> None:
        self.patch = patch
        self.refresh()

    def refresh(self) -> None:
        if not self.patch:
            return
        patch = self.patch
        self.title_label.setText(patch.name)
        dday_text, dday_color = dday_info(patch.due_date)
        self.due_label.setText(f"패치일 {patch.due_date}  {dday_text}")
        self.due_label.setStyleSheet(f"color: {dday_color}; font-weight: bold;")

        done, total = patch.progress
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(done)
        self.progress_label.setText(f"{patch.percent}%  ({done}/{total})")

        while self.cards_layout.count() > 1:
            entry = self.cards_layout.takeAt(0)
            if entry.widget():
                entry.widget().deleteLater()

        self.empty_label.setVisible(not patch.checklists)
        self.scroll.setVisible(bool(patch.checklists))
        for checklist in patch.checklists:
            card = ChecklistCard(checklist)
            card.clicked.connect(self.openChecklistRequested.emit)
            card.menuRequested.connect(self._show_card_menu)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    # ---- 동작 ----
    def _add_checklist(self) -> None:
        if not self.storage.presets:
            QMessageBox.information(
                self, "프리셋 없음",
                "체크리스트를 추가하려면 먼저 프리셋이 필요합니다.\n프리셋 메뉴에서 만들어주세요.",
            )
            return
        dialog = AddChecklistDialog(self.storage.presets, self)
        if dialog.exec():
            preset, country, name = dialog.result_values()
            checklist = create_checklist_from_preset(preset, country, name)
            self.patch.checklists.append(checklist)
            self.storage.save()
            self.refresh()

    def _show_card_menu(self, checklist_id: str, global_pos) -> None:
        checklist = next(
            (c for c in self.patch.checklists if c.id == checklist_id), None
        )
        if not checklist:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("이름 변경")
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(global_pos)
        if chosen == rename_action:
            text, ok = QInputDialog.getText(
                self, "이름 변경", "새 이름:", text=checklist.name
            )
            if ok and text.strip():
                checklist.name = text.strip()
        elif chosen == delete_action:
            answer = QMessageBox.question(
                self, "삭제", f'"{checklist.name}" 체크리스트를 삭제할까요?'
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.patch.checklists.remove(checklist)
        else:
            return
        self.storage.save()
        self.refresh()

    def maybe_archive_patch(self) -> bool:
        """패치 전체가 완료되면 보관 여부를 묻는다. 보관했으면 True."""
        if not self.patch or not self.patch.is_done or self.patch.is_archived:
            return False
        answer = QMessageBox.question(
            self,
            "패치 완료",
            f'"{self.patch.name}"의 모든 체크리스트가 완료되었습니다.\n'
            "완료 처리하고 보관함으로 이동할까요?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.patch.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.storage.save()
            self.archivedChanged.emit()
            return True
        return False
