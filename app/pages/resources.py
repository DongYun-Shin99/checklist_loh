"""리소스 경로 탭: 아이콘 등 자주 쓰는 리소스 폴더/파일 바로가기 모음."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import ResourceEntry
from ..storage import Storage
from ..utils import combined_path, open_in_explorer

ENTRY_ROLE = Qt.ItemDataRole.UserRole


class ResourceDialog(QDialog):
    """리소스 경로 추가/수정 다이얼로그 (폴더/파일 분리 입력)."""

    def __init__(self, parent=None, entry: ResourceEntry | None = None):
        super().__init__(parent)
        self.setWindowTitle("리소스 경로 수정" if entry else "리소스 경로 추가")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit(entry.name if entry else "")
        self.name_edit.setPlaceholderText("예: 영웅 아이콘")
        form.addRow("이름 (리소스 설명)", self.name_edit)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(entry.folder if entry else "")
        self.folder_edit.setPlaceholderText("폴더 경로")
        folder_row.addWidget(self.folder_edit, 1)
        folder_btn = QPushButton("폴더")
        folder_btn.setProperty("small", True)
        folder_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_btn)
        form.addRow("폴더 경로", folder_row)

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit(entry.file if entry else "")
        self.file_edit.setPlaceholderText("파일 명 (선택 — 비우면 폴더만)")
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

        self.name_edit.setFocus()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if path:
            self.folder_edit.setText(path)

    def _browse_file(self) -> None:
        """파일을 고르면 폴더/파일 칸이 자동으로 나뉘어 채워진다."""
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path:
            p = Path(path)
            self.folder_edit.setText(str(p.parent))
            self.file_edit.setText(p.name)

    def _on_accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "입력 필요", "이름(리소스 설명)을 입력해주세요.")
            return
        if not self.folder_edit.text().strip():
            QMessageBox.warning(self, "입력 필요", "폴더 경로를 입력해주세요.")
            return
        self.accept()

    def result_values(self) -> tuple[str, str, str]:
        return (
            self.name_edit.text().strip(),
            self.folder_edit.text().strip(),
            self.file_edit.text().strip(),
        )


class ResourcePage(QWidget):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("리소스 경로")
        title.setProperty("h1", True)
        layout.addWidget(title)

        subtitle = QLabel("아이콘 등 자주 쓰는 리소스의 폴더/파일 바로가기. 더블클릭으로 폴더를 엽니다.")
        subtitle.setProperty("muted", True)
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["이름", "폴더 경로", "파일 명"])
        self.tree.setColumnWidth(0, 180)
        self.tree.setColumnWidth(1, 360)
        self.tree.setRootIsDecorated(False)
        self.tree.itemDoubleClicked.connect(lambda *_: self._open_selected())
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        body.addWidget(self.tree, 1)

        # 우측 버튼 열
        buttons = QVBoxLayout()
        buttons.setSpacing(8)
        add_btn = QPushButton("＋ 항목 추가")
        add_btn.setProperty("primary", True)
        add_btn.clicked.connect(self._add_entry)
        buttons.addWidget(add_btn)
        edit_btn = QPushButton("항목 수정")
        edit_btn.clicked.connect(self._edit_selected)
        buttons.addWidget(edit_btn)
        delete_btn = QPushButton("항목 삭제")
        delete_btn.setProperty("danger", True)
        delete_btn.clicked.connect(self._delete_selected)
        buttons.addWidget(delete_btn)
        buttons.addSpacing(12)
        open_btn = QPushButton("폴더 열기")
        open_btn.clicked.connect(self._open_selected)
        buttons.addWidget(open_btn)
        buttons.addStretch()
        buttons_host = QWidget()
        buttons_host.setLayout(buttons)
        buttons_host.setFixedWidth(140)
        body.addWidget(buttons_host)

        layout.addLayout(body, 1)

        self.empty_label = QLabel("등록된 리소스 경로가 없습니다. [＋ 항목 추가]로 등록해보세요.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        self.tree.clear()
        self.empty_label.setVisible(not self.storage.resources)
        for entry in self.storage.resources:
            exists = os.path.exists(combined_path(entry.folder, entry.file))
            row = QTreeWidgetItem([
                entry.name,
                entry.folder + ("" if exists else "   ⚠ 경로 없음"),
                entry.file,
            ])
            row.setData(0, ENTRY_ROLE, entry)
            if not exists:
                row.setForeground(1, QBrush(QColor("#dc2626")))
            self.tree.addTopLevelItem(row)

    def _selected_entry(self) -> ResourceEntry | None:
        item = self.tree.currentItem()
        return item.data(0, ENTRY_ROLE) if item else None

    # ---- 동작 ----
    def _add_entry(self) -> None:
        dialog = ResourceDialog(self)
        if dialog.exec():
            name, folder, file = dialog.result_values()
            self.storage.resources.append(
                ResourceEntry(name=name, folder=folder, file=file)
            )
            self.storage.save()
            self.refresh()

    def _edit_selected(self) -> None:
        entry = self._selected_entry()
        if not entry:
            QMessageBox.information(self, "항목 수정", "수정할 항목을 먼저 선택해주세요.")
            return
        dialog = ResourceDialog(self, entry)
        if dialog.exec():
            entry.name, entry.folder, entry.file = dialog.result_values()
            self.storage.save()
            self.refresh()

    def _delete_selected(self) -> None:
        entry = self._selected_entry()
        if not entry:
            QMessageBox.information(self, "항목 삭제", "삭제할 항목을 먼저 선택해주세요.")
            return
        answer = QMessageBox.question(self, "삭제", f'"{entry.name}" 항목을 삭제할까요?')
        if answer == QMessageBox.StandardButton.Yes:
            self.storage.resources.remove(entry)
            self.storage.save()
            self.refresh()

    def _open_selected(self) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        full = combined_path(entry.folder, entry.file)
        if not os.path.exists(full):
            QMessageBox.warning(self, "경로 없음", f"경로가 존재하지 않습니다:\n{full}")
            return
        open_in_explorer(full)

    def _show_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        self.tree.setCurrentItem(item)
        menu = QMenu(self)
        open_action = menu.addAction("폴더 열기")
        edit_action = menu.addAction("수정")
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if chosen == open_action:
            self._open_selected()
        elif chosen == edit_action:
            self._edit_selected()
        elif chosen == delete_action:
            self._delete_selected()
