"""보관함 화면: 완료된 패치를 국가 단위로 그룹핑해서 보관."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
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
from ..models import COUNTRIES, COUNTRY_COLORS, Patch
from ..storage import Storage

PATCH_ROLE = Qt.ItemDataRole.UserRole
CHECKLIST_ROLE = Qt.ItemDataRole.UserRole + 1


def _on_time(patch: Patch) -> bool | None:
    """기한 내 완료 여부. 기한이 없으면 None."""
    if not patch.due_date or not patch.completed_at:
        return None
    try:
        due = date.fromisoformat(patch.due_date)
        completed = date.fromisoformat(patch.completed_at[:10])
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

        title = QLabel("보관함 (완료된 패치)")
        title.setProperty("h1", True)
        layout.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["이름", "정보", "완료일", "패치일"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 160)
        self.tree.setColumnWidth(2, 140)
        self.tree.itemDoubleClicked.connect(self._open_view)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        layout.addWidget(self.tree, 1)

        self.empty_label = QLabel("완료된 패치가 아직 없습니다.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        self.tree.clear()
        archived = self.storage.archived_patches()
        self.empty_label.setVisible(not archived)
        self.tree.setVisible(bool(archived))

        for code, country_name in COUNTRIES.items():
            group = [p for p in archived if p.country == code]
            if not group:
                continue
            country_node = QTreeWidgetItem([f"{country_name} ({len(group)})"])
            font = country_node.font(0)
            font.setBold(True)
            country_node.setFont(0, font)
            country_node.setForeground(
                0, QBrush(QColor(COUNTRY_COLORS.get(code, "#374151")))
            )
            self.tree.addTopLevelItem(country_node)

            for patch in sorted(group, key=lambda p: p.completed_at or "", reverse=True):
                on_time = _on_time(patch)
                if on_time is None:
                    due_text = patch.due_date or "기한 없음"
                elif on_time:
                    due_text = f"{patch.due_date} · 기한 내 ✓"
                else:
                    due_text = f"{patch.due_date} · 기한 초과 ⚠"
                patch_node = QTreeWidgetItem([
                    patch.name,
                    f"체크리스트 {len(patch.checklists)}개",
                    patch.completed_at or "-",
                    due_text,
                ])
                patch_node.setData(0, PATCH_ROLE, patch.id)
                if on_time is False:
                    patch_node.setForeground(3, Qt.GlobalColor.red)
                country_node.addChild(patch_node)

                for checklist in patch.checklists:
                    done, total = checklist.progress
                    child = QTreeWidgetItem([
                        checklist.name,
                        f"{checklist.preset_name} · {done}/{total}",
                        "", "",
                    ])
                    child.setData(0, PATCH_ROLE, patch.id)
                    child.setData(0, CHECKLIST_ROLE, checklist.id)
                    patch_node.addChild(child)
            country_node.setExpanded(True)

    def _resolve(self, item: QTreeWidgetItem):
        patch = self.storage.find_patch(item.data(0, PATCH_ROLE))
        checklist_id = item.data(0, CHECKLIST_ROLE)
        checklist = None
        if patch and checklist_id:
            checklist = next((c for c in patch.checklists if c.id == checklist_id), None)
        return patch, checklist

    def _open_view(self, item: QTreeWidgetItem, _column: int) -> None:
        patch, checklist = self._resolve(item)
        if patch and checklist:
            ArchiveViewDialog(patch, checklist, self).exec()

    def _show_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        patch, checklist = self._resolve(item)
        if not patch:
            return

        menu = QMenu(self)
        if checklist:
            view_action = menu.addAction("내용 보기")
            chosen = menu.exec(self.tree.mapToGlobal(pos))
            if chosen == view_action:
                ArchiveViewDialog(patch, checklist, self).exec()
            return

        restore_action = menu.addAction("진행 중으로 복원")
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if chosen == restore_action:
            patch.completed_at = None
            self.storage.save()
            self.refresh()
            self.restored.emit()
        elif chosen == delete_action:
            answer = QMessageBox.question(
                self, "삭제",
                f'"{patch.name}" 패치 기록을 완전히 삭제할까요?',
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.storage.patches.remove(patch)
                self.storage.save()
                self.refresh()
