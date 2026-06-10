"""진행 중인 패치 목록 화면 (메인). 패치일 + 전체 진행률만 심플하게 보여준다."""
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

from ..dialogs import NewPatchDialog
from ..models import Patch
from ..storage import Storage
from ..utils import dday_info


class PatchCard(QFrame):
    clicked = Signal(str)
    menuRequested = Signal(str, object)  # id, global pos

    def __init__(self, patch: Patch):
        super().__init__()
        self.patch_id = patch.id
        self.setProperty("card", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        name = QLabel(patch.name)
        name.setStyleSheet("font-size: 15px; font-weight: bold; border: none;")
        top.addWidget(name)
        count = QLabel(f"체크리스트 {len(patch.checklists)}개")
        count.setStyleSheet("color: #9ca3af; border: none; font-size: 12px;")
        top.addWidget(count)
        top.addStretch()
        dday_text, dday_color = dday_info(patch.due_date)
        due = QLabel(f"패치일 {patch.due_date}  {dday_text}")
        due.setStyleSheet(f"color: {dday_color}; font-weight: bold; border: none;")
        top.addWidget(due)
        layout.addLayout(top)

        done, total = patch.progress
        bottom = QHBoxLayout()
        bar = QProgressBar()
        bar.setMaximum(max(total, 1))
        bar.setValue(done)
        bar.setTextVisible(False)
        bottom.addWidget(bar, 1)
        percent = QLabel(f"{patch.percent}%")
        percent.setStyleSheet(
            "color: #2563eb; border: none; font-weight: bold; min-width: 38px;"
        )
        percent.setAlignment(Qt.AlignmentFlag.AlignRight)
        bottom.addWidget(percent)
        layout.addLayout(bottom)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.patch_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.menuRequested.emit(self.patch_id, event.globalPos())


class PatchListPage(QWidget):
    openRequested = Signal(str)  # patch id
    dataChanged = Signal()

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("진행 중인 패치")
        title.setProperty("h1", True)
        header.addWidget(title)
        header.addStretch()
        new_btn = QPushButton("＋ 새 패치")
        new_btn.setProperty("primary", True)
        new_btn.clicked.connect(self._create_patch)
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
            "진행 중인 패치가 없습니다.\n[＋ 새 패치]로 패치일을 정해 만들어보세요."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        while self.cards_layout.count() > 1:
            entry = self.cards_layout.takeAt(0)
            if entry.widget():
                entry.widget().deleteLater()

        active = self.storage.active_patches()
        self.empty_label.setVisible(not active)
        self.scroll.setVisible(bool(active))

        def sort_key(p: Patch):
            try:
                return (0, date.fromisoformat(p.due_date))
            except ValueError:
                return (1, date.max)

        for patch in sorted(active, key=sort_key):
            card = PatchCard(patch)
            card.clicked.connect(self.openRequested.emit)
            card.menuRequested.connect(self._show_card_menu)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    # ---- 동작 ----
    def _create_patch(self) -> None:
        dialog = NewPatchDialog(self)
        if dialog.exec():
            name, due = dialog.result_values()
            patch = Patch(
                name=name,
                due_date=due,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            self.storage.patches.append(patch)
            self.storage.save()
            self.refresh()
            self.openRequested.emit(patch.id)

    def _show_card_menu(self, patch_id: str, global_pos) -> None:
        patch = self.storage.find_patch(patch_id)
        if not patch:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("이름 변경")
        due_action = menu.addAction("패치일 변경")
        archive_action = menu.addAction("보관함으로 이동") if patch.is_done else None
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == rename_action:
            text, ok = QInputDialog.getText(self, "이름 변경", "새 이름:", text=patch.name)
            if ok and text.strip():
                patch.name = text.strip()
        elif chosen == due_action:
            text, ok = QInputDialog.getText(
                self, "패치일 변경", "패치일 (YYYY-MM-DD):", text=patch.due_date
            )
            if ok:
                try:
                    date.fromisoformat(text.strip())
                    patch.due_date = text.strip()
                except ValueError:
                    QMessageBox.warning(self, "형식 오류", "YYYY-MM-DD 형식으로 입력해주세요.")
        elif archive_action and chosen == archive_action:
            patch.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.dataChanged.emit()
        elif chosen == delete_action:
            answer = QMessageBox.question(
                self, "삭제",
                f'"{patch.name}" 패치를 삭제할까요?\n안의 체크리스트도 함께 삭제됩니다.',
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.storage.patches.remove(patch)
        self.storage.save()
        self.refresh()
