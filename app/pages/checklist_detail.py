"""체크리스트 상세 화면: 항목/하위 항목 체크, 경로 열기, 메모, 즉석 항목 추가."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..dialogs import ResourcePickerDialog
from ..models import Checklist, ChecklistItem, Patch, join_base
from ..storage import Storage
from ..utils import combined_path, dday_info, open_in_explorer, path_display
from ..widgets import country_badge


class ChecklistItemDialog(QDialog):
    """체크리스트 항목 추가/수정 다이얼로그 (이미 국가가 정해진 인스턴스용)."""

    def __init__(
        self,
        parent=None,
        item: ChecklistItem | None = None,
        title: str = "",
        base_folder: str = "",
        resources: list | None = None,
    ):
        super().__init__(parent)
        self._base_folder = base_folder
        self._resources = resources or []
        self.setWindowTitle(title or ("항목 수정" if item else "항목 추가"))
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.desc_edit = QLineEdit(item.description if item else "")
        self.desc_edit.setPlaceholderText("예: Gacha 테이블 수정")
        form.addRow("작업 설명", self.desc_edit)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(item.folder if item else "")
        self.folder_edit.setPlaceholderText("폴더 경로 (선택)")
        folder_row.addWidget(self.folder_edit, 1)
        if base_folder:
            base_btn = QPushButton("기본 폴더")
            base_btn.setProperty("small", True)
            base_btn.setToolTip(f"설정의 기본 폴더 삽입: {base_folder}")
            base_btn.clicked.connect(lambda: self.folder_edit.setText(base_folder))
            folder_row.addWidget(base_btn)
        folder_btn = QPushButton("폴더")
        folder_btn.setProperty("small", True)
        folder_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_btn)
        if self._resources:
            resource_btn = QPushButton("리소스")
            resource_btn.setProperty("small", True)
            resource_btn.setToolTip("리소스 경로 탭에 등록된 경로 불러오기 (이 패치의 빌드로 연결)")
            resource_btn.clicked.connect(self._pick_resource)
            folder_row.addWidget(resource_btn)
        form.addRow("폴더 경로", folder_row)

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit(item.file if item else "")
        self.file_edit.setPlaceholderText("파일 명 (선택)")
        file_row.addWidget(self.file_edit, 1)
        file_btn = QPushButton("파일")
        file_btn.setProperty("small", True)
        file_btn.clicked.connect(self._browse_file)
        file_row.addWidget(file_btn)
        form.addRow("파일 명", file_row)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("확인")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.desc_edit.setFocus()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if path:
            self.folder_edit.setText(path)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path:
            p = Path(path)
            self.folder_edit.setText(str(p.parent))
            self.file_edit.setText(p.name)

    def _pick_resource(self) -> None:
        """리소스 경로를 골라 이 패치의 빌드(기본 폴더)에 맞는 경로로 넣는다."""
        dialog = ResourcePickerDialog(self._resources, self)
        if dialog.exec() and dialog.selected():
            res = dialog.selected()
            self.folder_edit.setText(join_base(self._base_folder, res.folder))
            self.file_edit.setText(res.file)

    def _on_accept(self) -> None:
        if not self.desc_edit.text().strip():
            QMessageBox.warning(self, "입력 필요", "작업 설명을 입력해주세요.")
            return
        self.accept()

    def result_values(self) -> tuple[str, str, str]:
        return (
            self.desc_edit.text().strip(),
            self.folder_edit.text().strip(),
            self.file_edit.text().strip(),
        )


class ItemRow(QFrame):
    statusChanged = Signal()
    menuRequested = Signal(object, object)  # item, global pos

    def __init__(self, item: ChecklistItem, storage: Storage, is_child: bool = False):
        super().__init__()
        self.item = item
        self.storage = storage
        self.is_child = is_child
        self.setProperty("card", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self.checkbox = QCheckBox(item.description)
        self.checkbox.setChecked(item.is_done)
        self.checkbox.clicked.connect(self._on_clicked)
        top.addWidget(self.checkbox)
        self.memo_edit = QLineEdit(item.memo)
        self.memo_edit.setProperty("flat", True)
        self.memo_edit.setPlaceholderText("메모 추가...")
        self.memo_edit.textEdited.connect(self._on_memo_edited)
        top.addWidget(self.memo_edit, 1)
        self.status_label = QLabel()
        top.addWidget(self.status_label)
        layout.addLayout(top)

        if item.folder or item.file:
            path_row = QHBoxLayout()
            path_row.setContentsMargins(26, 0, 0, 0)
            full = combined_path(item.folder, item.file)
            exists = os.path.exists(full)
            path_label = QLabel(
                path_display(item.folder, item.file) + ("" if exists else "   ⚠ 경로 없음")
            )
            path_label.setStyleSheet(
                "border: none; font-size: 12px; color: "
                + ("#6b7280" if exists else "#dc2626")
            )
            path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            path_row.addWidget(path_label, 1)
            open_btn = QPushButton("열기")
            open_btn.setProperty("small", True)
            open_btn.setEnabled(exists)
            open_btn.clicked.connect(lambda: open_in_explorer(full))
            path_row.addWidget(open_btn)
            layout.addLayout(path_row)

        self._apply_status_style()

    def contextMenuEvent(self, event):
        self.menuRequested.emit(self.item, event.globalPos())

    def _on_clicked(self, checked: bool) -> None:
        self.item.set_done(checked)
        self.storage.save()
        self._apply_status_style()
        self.statusChanged.emit()

    def _on_memo_edited(self, text: str) -> None:
        self.item.memo = text
        self.storage.save()

    def _apply_status_style(self) -> None:
        if self.item.is_done:
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
    checklistCompleted = Signal()  # 마지막 항목 완료 시 (패치 보관 여부 확인용)

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.patch: Patch | None = None
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
        add_btn = QPushButton("＋ 항목 추가")
        add_btn.setProperty("primary", True)
        add_btn.clicked.connect(self._add_item)
        header.addWidget(add_btn)
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

        self.empty_label = QLabel("항목이 없습니다. [＋ 항목 추가]로 작업을 추가해보세요.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def set_checklist(self, patch: Patch, checklist: Checklist) -> None:
        self.patch = patch
        self.checklist = checklist
        self.refresh()

    def refresh(self) -> None:
        if not self.checklist:
            return
        c = self.checklist
        self.title_label.setText(f"{self.patch.name} · {c.name}")

        while self.badge_host.count():
            entry = self.badge_host.takeAt(0)
            if entry.widget():
                entry.widget().deleteLater()
        self.badge_host.addWidget(country_badge(self.patch.country))

        dday_text, dday_color = dday_info(self.patch.due_date)
        self.dday_label.setText(f"패치일 {self.patch.due_date or '없음'}  {dday_text}")
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
            entry = self.items_layout.takeAt(0)
            if entry.widget():
                entry.widget().deleteLater()
            elif entry.layout():
                self._clear_layout(entry.layout())

        self.empty_label.setVisible(not self.checklist.items)

        items = list(self.checklist.items)
        if self.sort_toggle.isChecked():
            items.sort(key=lambda i: i.is_done)  # 진행중 먼저, 원래 순서 유지(안정 정렬)
        for item in items:
            self._insert_row(item, is_child=False)
            children = list(item.children)
            if self.sort_toggle.isChecked():
                children.sort(key=lambda i: i.is_done)
            for child in children:
                self._insert_row(child, is_child=True)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            entry = layout.takeAt(0)
            if entry.widget():
                entry.widget().deleteLater()

    def _insert_row(self, item: ChecklistItem, is_child: bool) -> None:
        row = ItemRow(item, self.storage, is_child=is_child)
        row.statusChanged.connect(self._on_item_status_changed)
        row.menuRequested.connect(self._show_item_menu)
        if is_child:
            wrapper = QHBoxLayout()
            wrapper.addSpacing(34)
            wrapper.addWidget(row)
            self.items_layout.insertLayout(self.items_layout.count() - 1, wrapper)
        else:
            self.items_layout.insertWidget(self.items_layout.count() - 1, row)

    def _on_item_status_changed(self) -> None:
        self._update_progress()
        if self.checklist.is_done:
            self.checklistCompleted.emit()
        # 부모/하위 상태 표시 동기화를 위해 다시 그린다 (시그널 처리 후로 미룸)
        QTimer.singleShot(0, self._rebuild_items)

    # ---- 항목 추가/수정/삭제 ----
    def _find_parent_list(self, item: ChecklistItem) -> list | None:
        if item in self.checklist.items:
            return self.checklist.items
        for top in self.checklist.items:
            if item in top.children:
                return top.children
        return None

    def _base_folder(self) -> str:
        return self.storage.base_paths().get(self.patch.country, "") if self.patch else ""

    def _add_item(self) -> None:
        dialog = ChecklistItemDialog(
            self, title="항목 추가",
            base_folder=self._base_folder(), resources=self.storage.resources,
        )
        if dialog.exec():
            desc, folder, file = dialog.result_values()
            self.checklist.items.append(
                ChecklistItem(description=desc, folder=folder, file=file)
            )
            self.storage.save()
            self._update_progress()
            self._rebuild_items()

    def _show_item_menu(self, item: ChecklistItem, global_pos) -> None:
        menu = QMenu(self)
        edit_action = menu.addAction("항목 수정")
        child_action = None
        if item in self.checklist.items:  # 깊이 1단계 제한
            child_action = menu.addAction("하위 항목 추가")
        menu.addSeparator()
        delete_action = menu.addAction("항목 삭제")
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == edit_action:
            dialog = ChecklistItemDialog(
                self, item=item,
                base_folder=self._base_folder(), resources=self.storage.resources,
            )
            if dialog.exec():
                item.description, item.folder, item.file = dialog.result_values()
        elif child_action and chosen == child_action:
            dialog = ChecklistItemDialog(
                self, title="하위 항목 추가",
                base_folder=self._base_folder(), resources=self.storage.resources,
            )
            if dialog.exec():
                desc, folder, file = dialog.result_values()
                item.children.append(
                    ChecklistItem(description=desc, folder=folder, file=file)
                )
        elif chosen == delete_action:
            label = f'"{item.description}"'
            warn = " 하위 항목도 함께 삭제됩니다." if item.children else ""
            answer = QMessageBox.question(self, "항목 삭제", f"{label} 항목을 삭제할까요?{warn}")
            if answer != QMessageBox.StandardButton.Yes:
                return
            siblings = self._find_parent_list(item)
            if siblings is not None:
                siblings.remove(item)
        else:
            return
        self.storage.save()
        self._update_progress()
        self._rebuild_items()
