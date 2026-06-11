"""다이얼로그: 새 패치, 체크리스트 추가, 보관함 읽기 전용 보기."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QTextBrowser,
    QVBoxLayout,
)

from .models import COUNTRIES, Checklist, Patch, Preset


def _ok_cancel(ok_text: str) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
    return buttons


class NewPatchDialog(QDialog):
    """패치일(기한)과 국가를 정해서 새 패치를 만드는 다이얼로그."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 패치")
        self.setMinimumWidth(360)
        self._name_edited = False

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.due_edit = QDateEdit()
        self.due_edit.setCalendarPopup(True)
        default_due = date.today() + timedelta(days=7)
        self.due_edit.setDate(QDate(default_due.year, default_due.month, default_due.day))
        self.due_edit.dateChanged.connect(self._update_default_name)

        self.country_combo = QComboBox()
        for code, name in COUNTRIES.items():
            self.country_combo.addItem(name, code)
        self.country_combo.currentIndexChanged.connect(self._update_default_name)

        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_name_edited)

        form.addRow("패치일", self.due_edit)
        form.addRow("국가", self.country_combo)
        form.addRow("이름", self.name_edit)
        layout.addLayout(form)

        buttons = _ok_cancel("생성")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_default_name()

    def _on_name_edited(self) -> None:
        self._name_edited = True

    def _update_default_name(self) -> None:
        if self._name_edited and self.name_edit.text().strip():
            return
        d = self.due_edit.date()
        self.name_edit.setText(f"{d.month()}/{d.day()} {self.country_combo.currentText()} 패치")
        self._name_edited = False

    def result_values(self) -> tuple[str, str, str]:
        due = self.due_edit.date().toString("yyyy-MM-dd")
        country = self.country_combo.currentData()
        name = self.name_edit.text().strip() or f"{due} 패치"
        return name, country, due


class AddChecklistDialog(QDialog):
    """패치에 작업 묶음(체크리스트)을 추가하는 다이얼로그. 국가는 패치를 따라간다.

    프리셋에서 가져오거나, 루틴 외 작업을 위한 빈 체크리스트를 만들 수 있다.
    """

    def __init__(self, presets: list[Preset], patch: Patch, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"체크리스트 추가 — {patch.name} ({patch.country_name})")
        self.setMinimumWidth(420)
        self._name_edited = False

        layout = QVBoxLayout(self)

        self.preset_radio = QRadioButton("프리셋에서 가져오기 (루틴 업무)")
        self.empty_radio = QRadioButton("빈 체크리스트 (항목 직접 추가)")
        layout.addWidget(self.preset_radio)
        layout.addWidget(self.empty_radio)

        form = QFormLayout()
        form.setSpacing(10)

        self.preset_combo = QComboBox()
        for p in presets:
            self.preset_combo.addItem(f"{p.name} ({len(p.items)}개 항목)", p)

        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_name_edited)

        form.addRow("프리셋", self.preset_combo)
        form.addRow("이름", self.name_edit)
        layout.addLayout(form)

        buttons = _ok_cancel("추가")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.preset_radio.toggled.connect(self._on_mode_changed)
        self.preset_combo.currentIndexChanged.connect(self._update_default_name)

        if presets:
            self.preset_radio.setChecked(True)
        else:
            self.preset_radio.setEnabled(False)
            self.preset_radio.setText("프리셋에서 가져오기 (프리셋 없음)")
            self.empty_radio.setChecked(True)
        self._on_mode_changed()

    def _on_mode_changed(self, *_):
        from_preset = self.preset_radio.isChecked()
        self.preset_combo.setEnabled(from_preset)
        self._update_default_name()

    def _on_name_edited(self) -> None:
        self._name_edited = True

    def _update_default_name(self) -> None:
        if self._name_edited and self.name_edit.text().strip():
            return
        if self.preset_radio.isChecked():
            preset = self.preset_combo.currentData()
            if preset:
                self.name_edit.setText(preset.name)
        else:
            self.name_edit.setText("새 체크리스트")
        self._name_edited = False

    def result_values(self) -> tuple[Preset | None, str]:
        """선택한 (프리셋 또는 None, 이름). 프리셋이 None이면 빈 체크리스트."""
        preset = self.preset_combo.currentData() if self.preset_radio.isChecked() else None
        default = preset.name if preset else "새 체크리스트"
        name = self.name_edit.text().strip() or default
        return preset, name


class ResourcePickerDialog(QDialog):
    """저장된 리소스 경로 중 하나를 골라 항목 경로로 넣는 팝업."""

    def __init__(self, resources: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("리소스 경로에서 선택")
        self.resize(520, 380)
        self._resources = resources

        layout = QVBoxLayout(self)
        hint = QLabel("리소스 경로 탭에 등록된 항목입니다. 더블클릭 또는 선택 후 [선택].")
        hint.setProperty("muted", True)
        layout.addWidget(hint)

        self.list = QListWidget()
        for res in resources:
            path_text = res.folder + (f"  📄 {res.file}" if res.file else "")
            entry = QListWidgetItem(f"{res.name}\n    {path_text}")
            entry.setData(Qt.ItemDataRole.UserRole, res)
            self.list.addItem(entry)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())
        layout.addWidget(self.list, 1)

        buttons = _ok_cancel("선택")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self.list.count():
            self.list.setCurrentRow(0)

    def selected(self):
        entry = self.list.currentItem()
        return entry.data(Qt.ItemDataRole.UserRole) if entry else None


class ArchiveViewDialog(QDialog):
    """완료된 체크리스트의 읽기 전용 상세 보기."""

    def __init__(self, patch: Patch, checklist: Checklist, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{checklist.name} (완료)")
        self.resize(560, 480)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(self._build_html(patch, checklist))
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("닫기")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _build_html(patch: Patch, c: Checklist) -> str:
        def render(item, indent: int) -> str:
            mark = "✔" if item.is_done else "○"
            color = "#059669" if item.is_done else "#d97706"
            margin = indent * 22
            path_text = "   ".join(
                part for part in (
                    f"📁 {item.folder}" if item.folder else "",
                    f"📄 {item.file}" if item.file else "",
                ) if part
            )
            path_line = (
                f'<div style="color:#6b7280; font-size:12px;">{path_text}</div>'
                if path_text
                else ""
            )
            memo_line = (
                f'<div style="color:#92400e; font-size:12px;">📝 {item.memo}</div>'
                if item.memo
                else ""
            )
            html = (
                f'<div style="margin: 0 0 10px {margin}px;">'
                f'<span style="color:{color}; font-weight:bold;">{mark}</span> '
                f"{item.description}{path_line}{memo_line}</div>"
            )
            for child in item.children:
                html += render(child, indent + 1)
            return html

        rows = [render(item, 0) for item in c.items]
        header = (
            f"<h3>{c.name}</h3>"
            f'<p style="color:#6b7280;">패치: {patch.name} · 프리셋: {c.preset_name or "직접 작성"} · 국가: {patch.country_name}<br>'
            f"패치일: {patch.due_date or '없음'} · 완료일: {patch.completed_at or '-'}</p><hr>"
        )
        return header + "".join(rows)
