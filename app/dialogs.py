"""다이얼로그: 새 체크리스트 생성, 보관함 읽기 전용 보기."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextBrowser,
    QVBoxLayout,
)

from .models import COUNTRIES, Checklist, Preset


class NewChecklistDialog(QDialog):
    """프리셋 + 국가 + 기한을 정해서 체크리스트를 생성하는 다이얼로그."""

    def __init__(self, presets: list[Preset], parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 체크리스트")
        self.setMinimumWidth(380)
        self._presets = presets
        self._name_edited = False

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.preset_combo = QComboBox()
        for p in presets:
            self.preset_combo.addItem(f"{p.name} ({len(p.items)}개 항목)", p)

        self.country_combo = QComboBox()
        for code, name in COUNTRIES.items():
            self.country_combo.addItem(name, code)

        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_name_edited)

        self.due_edit = QDateEdit()
        self.due_edit.setCalendarPopup(True)
        default_due = date.today() + timedelta(days=7)
        self.due_edit.setDate(QDate(default_due.year, default_due.month, default_due.day))

        form.addRow("프리셋", self.preset_combo)
        form.addRow("국가", self.country_combo)
        form.addRow("이름", self.name_edit)
        form.addRow("작업 기한", self.due_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("생성")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.preset_combo.currentIndexChanged.connect(self._update_default_name)
        self.country_combo.currentIndexChanged.connect(self._update_default_name)
        self._update_default_name()

    def _on_name_edited(self) -> None:
        self._name_edited = True

    def _update_default_name(self) -> None:
        if self._name_edited and self.name_edit.text().strip():
            return
        preset = self.preset_combo.currentData()
        country = self.country_combo.currentText()
        if preset:
            self.name_edit.setText(f"{preset.name} - {country}")
            self._name_edited = False

    def result_values(self) -> tuple[Preset, str, str, str]:
        preset = self.preset_combo.currentData()
        country_code = self.country_combo.currentData()
        name = self.name_edit.text().strip() or f"{preset.name} - {self.country_combo.currentText()}"
        due = self.due_edit.date().toString("yyyy-MM-dd")
        return preset, country_code, name, due


class ArchiveViewDialog(QDialog):
    """완료된 체크리스트의 읽기 전용 상세 보기."""

    def __init__(self, checklist: Checklist, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{checklist.name} (완료)")
        self.resize(560, 480)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(self._build_html(checklist))
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("닫기")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _build_html(c: Checklist) -> str:
        rows = []
        for item in c.items:
            mark = "✔" if item.done else "○"
            color = "#059669" if item.done else "#d97706"
            path_line = (
                f'<div style="color:#6b7280; font-size:12px;">📁 {item.path}</div>'
                if item.path
                else ""
            )
            memo_line = (
                f'<div style="color:#92400e; font-size:12px;">📝 {item.memo}</div>'
                if item.memo
                else ""
            )
            rows.append(
                f'<div style="margin-bottom:10px;">'
                f'<span style="color:{color}; font-weight:bold;">{mark}</span> '
                f"{item.description}{path_line}{memo_line}</div>"
            )
        header = (
            f"<h3>{c.name}</h3>"
            f'<p style="color:#6b7280;">프리셋: {c.preset_name} · 국가: {c.country_name}<br>'
            f"기한: {c.due_date or '없음'} · 완료일: {c.completed_at or '-'}</p><hr>"
        )
        return header + "".join(rows)
