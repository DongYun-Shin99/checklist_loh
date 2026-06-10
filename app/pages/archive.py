"""보관함 화면: 완료된 체크리스트를 국가 단위로 그룹핑해서 표시."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..dialogs import ArchiveViewDialog
from ..models import COUNTRIES, COUNTRY_COLORS, Checklist
from ..storage import Storage

ID_ROLE = Qt.ItemDataRole.UserRole


def _on_time(c: Checklist) -> bool | None:
    """기한 내 완료 여부. 기한이 없으면 None."""
    if not c.due_date or not c.completed_at:
        return None
    try:
        due = date.fromisoformat(c.due_date)
        completed = date.fromisoformat(c.completed_at[:10])
    except ValueError:
        return None
    return completed <= due


class ArchivePage(QWidget):
    restored = Signal()

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("보관함 (완료된 작업)")
        title.setProperty("h1", True)
        layout.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["이름", "프리셋", "완료일", "기한"])
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 140)
        self.tree.itemDoubleClicked.connect(self._open_view)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        layout.addWidget(self.tree, 1)

        self.empty_label = QLabel("완료된 체크리스트가 아직 없습니다.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        self.tree.clear()
        archived = self.storage.archived_checklists()
        self.empty_label.setVisible(not archived)
        self.tree.setVisible(bool(archived))

        for code, country_name in COUNTRIES.items():
            group = [c for c in archived if c.country == code]
            if not group:
                continue
            top = QTreeWidgetItem([f"{country_name} ({len(group)})"])
            top.setFirstColumnSpanned(True)
            top.setForeground(0, Qt.GlobalColor.white)
            font = top.font(0)
            font.setBold(True)
            top.setFont(0, font)
            top.setBackground(0, self.palette().base())
            top.setForeground(0, self._country_brush(code))
            self.tree.addTopLevelItem(top)
            for c in sorted(group, key=lambda x: x.completed_at or "", reverse=True):
                on_time = _on_time(c)
                if on_time is None:
                    due_text = c.due_date or "기한 없음"
                elif on_time:
                    due_text = f"{c.due_date} · 기한 내 ✓"
                else:
                    due_text = f"{c.due_date} · 기한 초과 ⚠"
                child = QTreeWidgetItem([c.name, c.preset_name, c.completed_at or "-", due_text])
                child.setData(0, ID_ROLE, c.id)
                if on_time is False:
                    child.setForeground(3, Qt.GlobalColor.red)
                top.addChild(child)
            top.setExpanded(True)

    @staticmethod
    def _country_brush(code: str):
        from PySide6.QtGui import QBrush, QColor

        return QBrush(QColor(COUNTRY_COLORS.get(code, "#374151")))

    def _checklist_at(self, item: QTreeWidgetItem) -> Checklist | None:
        checklist_id = item.data(0, ID_ROLE)
        return self.storage.find_checklist(checklist_id) if checklist_id else None

    def _open_view(self, item: QTreeWidgetItem, _column: int) -> None:
        checklist = self._checklist_at(item)
        if checklist:
            ArchiveViewDialog(checklist, self).exec()

    def _show_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        checklist = self._checklist_at(item)
        if not checklist:
            return
        menu = QMenu(self)
        view_action = menu.addAction("내용 보기")
        restore_action = menu.addAction("진행 중으로 복원")
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if chosen == view_action:
            ArchiveViewDialog(checklist, self).exec()
        elif chosen == restore_action:
            checklist.completed_at = None
            self.storage.save()
            self.refresh()
            self.restored.emit()
        elif chosen == delete_action:
            answer = QMessageBox.question(
                self, "삭제", f'"{checklist.name}" 기록을 완전히 삭제할까요?'
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.storage.checklists.remove(checklist)
                self.storage.save()
                self.refresh()
