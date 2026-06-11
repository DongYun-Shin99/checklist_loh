"""설정 탭: 빌드(국가)별 기본 폴더 경로."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import COUNTRIES
from ..storage import Storage


class SettingsPage(QWidget):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("설정")
        title.setProperty("h1", True)
        layout.addWidget(title)

        card = QFrame()
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        section = QLabel("빌드별 기본 폴더 (SVN 트렁크 루트)")
        section.setStyleSheet("font-weight: bold; border: none;")
        card_layout.addWidget(section)

        hint = QLabel(
            "프리셋 항목의 상대 경로는 이 기본 폴더 아래에 붙습니다.\n"
            "예: 기본 폴더 C:\\00.SVN\\00.KR_LOH_Trunk + 상대 경로 Assets\\DB"
            " → C:\\00.SVN\\00.KR_LOH_Trunk\\Assets\\DB"
        )
        hint.setProperty("muted", True)
        hint.setStyleSheet("border: none; color: #6b7280;")
        card_layout.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.base_edits: dict[str, QLineEdit] = {}
        self.status_labels: dict[str, QLabel] = {}
        for row, (code, country_name) in enumerate(COUNTRIES.items()):
            label = QLabel(country_name)
            label.setFixedWidth(40)
            label.setStyleSheet("border: none;")
            grid.addWidget(label, row, 0)

            edit = QLineEdit()
            edit.setPlaceholderText(f"예: C:\\00.SVN\\00.{code}_LOH_Trunk")
            edit.textEdited.connect(lambda text, c=code: self._on_edited(c, text))
            grid.addWidget(edit, row, 1)

            browse_btn = QPushButton("폴더")
            browse_btn.setProperty("small", True)
            browse_btn.clicked.connect(lambda _, c=code: self._browse(c))
            grid.addWidget(browse_btn, row, 2)

            status = QLabel()
            status.setStyleSheet("border: none; font-size: 12px;")
            status.setFixedWidth(90)
            grid.addWidget(status, row, 3)

            self.base_edits[code] = edit
            self.status_labels[code] = status
        grid.setColumnStretch(1, 1)
        card_layout.addLayout(grid)
        layout.addWidget(card)
        layout.addStretch()

    def refresh(self) -> None:
        self._loading = True
        for code, edit in self.base_edits.items():
            edit.setText(self.storage.base_paths().get(code, ""))
            self._update_status(code)
        self._loading = False

    def _on_edited(self, code: str, text: str) -> None:
        if self._loading:
            return
        self.storage.base_paths()[code] = text.strip()
        self.storage.save()
        self._update_status(code)

    def _browse(self, code: str) -> None:
        path = QFileDialog.getExistingDirectory(self, f"{COUNTRIES[code]} 기본 폴더 선택")
        if path:
            self.base_edits[code].setText(path)
            self.storage.base_paths()[code] = path
            self.storage.save()
            self._update_status(code)

    def _update_status(self, code: str) -> None:
        path = self.base_edits[code].text().strip()
        status = self.status_labels[code]
        if not path:
            status.setText("미설정")
            status.setStyleSheet("border:none; font-size:12px; color:#9ca3af;")
        elif os.path.isdir(path):
            status.setText("확인됨 ✓")
            status.setStyleSheet("border:none; font-size:12px; color:#059669;")
        else:
            status.setText("⚠ 폴더 없음")
            status.setStyleSheet("border:none; font-size:12px; color:#dc2626;")
