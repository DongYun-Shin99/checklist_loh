"""설정 탭: 빌드(국가)별 기본 폴더 경로."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import COUNTRIES
from ..storage import Storage
from ..utils import autostart_available, get_autostart, set_autostart


def _card(title_text: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setProperty("card", True)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    title = QLabel(title_text)
    title.setStyleSheet("font-weight: bold; border: none;")
    layout.addWidget(title)
    return card, layout


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

        # ---- 윈도우 시작 시 자동 실행 ----
        run_card, run_layout = _card("실행")
        self.autostart_check = QCheckBox("윈도우 시작 시 자동 실행")
        self.autostart_check.toggled.connect(self._on_autostart_toggled)
        run_layout.addWidget(self.autostart_check)
        if not autostart_available():
            self.autostart_check.setEnabled(False)
            note = QLabel("※ exe로 빌드된 버전을 실행할 때만 설정할 수 있습니다.")
            note.setStyleSheet("border: none; color: #9ca3af; font-size: 12px;")
            run_layout.addWidget(note)
        layout.addWidget(run_card)

        # ---- 프리셋 자동 내보내기 ----
        export_card, export_layout = _card("프리셋 자동 내보내기")
        export_hint = QLabel(
            "켜두면 프리셋이 바뀔 때마다 아래 폴더에 프리셋별 .json 파일로 자동 저장됩니다.\n"
            "공유 폴더(SVN 등)를 지정하면 동료와 프리셋을 자동으로 공유할 수 있습니다."
        )
        export_hint.setStyleSheet("border: none; color: #6b7280;")
        export_layout.addWidget(export_hint)

        self.auto_export_check = QCheckBox("프리셋 변경 시 자동 내보내기")
        self.auto_export_check.toggled.connect(self._on_auto_export_toggled)
        export_layout.addWidget(self.auto_export_check)

        folder_row = QHBoxLayout()
        folder_label = QLabel("저장 폴더")
        folder_label.setStyleSheet("border: none;")
        folder_row.addWidget(folder_label)
        self.export_folder_edit = QLineEdit()
        self.export_folder_edit.setPlaceholderText("프리셋 .json을 저장할 폴더")
        self.export_folder_edit.textEdited.connect(self._on_export_folder_edited)
        folder_row.addWidget(self.export_folder_edit, 1)
        export_browse_btn = QPushButton("폴더")
        export_browse_btn.setProperty("small", True)
        export_browse_btn.clicked.connect(self._browse_export_folder)
        folder_row.addWidget(export_browse_btn)
        export_layout.addLayout(folder_row)
        layout.addWidget(export_card)

        layout.addStretch()

    def refresh(self) -> None:
        self._loading = True
        for code, edit in self.base_edits.items():
            edit.setText(self.storage.base_paths().get(code, ""))
            self._update_status(code)
        self.autostart_check.setChecked(get_autostart())
        self.auto_export_check.setChecked(bool(self.storage.settings.get("auto_export")))
        self.export_folder_edit.setText(self.storage.settings.get("export_folder", ""))
        self._loading = False

    # ---- 자동 실행 / 자동 내보내기 ----
    def _on_autostart_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        set_autostart(checked)

    def _on_auto_export_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        self.storage.settings["auto_export"] = checked
        self.storage.save()  # 켜는 순간 한 번 즉시 내보내기

    def _on_export_folder_edited(self, text: str) -> None:
        if self._loading:
            return
        self.storage.settings["export_folder"] = text.strip()
        self.storage.save()

    def _browse_export_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "프리셋 저장 폴더 선택")
        if path:
            self.export_folder_edit.setText(path)
            self.storage.settings["export_folder"] = path
            self.storage.save()

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
