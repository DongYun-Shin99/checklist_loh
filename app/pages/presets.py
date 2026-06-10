"""프리셋 관리 화면: 목록 + 편집기, 내보내기/불러오기."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import COUNTRIES, Preset, PresetItem, new_id
from ..storage import Storage

ITEM_ROLE = Qt.ItemDataRole.UserRole


class PresetPage(QWidget):
    presetsChanged = Signal()

    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.current_preset: Preset | None = None
        self.current_item: PresetItem | None = None
        self._loading = False

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ---- 왼쪽: 프리셋 목록 ----
        left = QVBoxLayout()
        left.setSpacing(8)
        title = QLabel("프리셋")
        title.setProperty("h1", True)
        left.addWidget(title)

        self.preset_list = QListWidget()
        self.preset_list.currentItemChanged.connect(self._on_preset_selected)
        self.preset_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preset_list.customContextMenuRequested.connect(self._show_preset_menu)
        left.addWidget(self.preset_list, 1)

        new_btn = QPushButton("＋ 새 프리셋")
        new_btn.setProperty("primary", True)
        new_btn.clicked.connect(self._create_preset)
        left.addWidget(new_btn)
        export_btn = QPushButton("내보내기 (JSON)")
        export_btn.clicked.connect(self._export_preset)
        left.addWidget(export_btn)
        import_btn = QPushButton("불러오기 (JSON)")
        import_btn.clicked.connect(self._import_preset)
        left.addWidget(import_btn)

        left_host = QWidget()
        left_host.setLayout(left)
        left_host.setFixedWidth(230)
        root.addWidget(left_host)

        # ---- 오른쪽: 편집기 ----
        right = QVBoxLayout()
        right.setSpacing(10)

        meta_form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_meta_edited)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("프리셋 설명 (선택)")
        self.desc_edit.textEdited.connect(self._on_meta_edited)
        meta_form.addRow("이름", self.name_edit)
        meta_form.addRow("설명", self.desc_edit)
        right.addLayout(meta_form)

        items_header = QHBoxLayout()
        items_label = QLabel("항목 (드래그로 순서 변경)")
        items_label.setProperty("muted", True)
        items_header.addWidget(items_label)
        items_header.addStretch()
        add_item_btn = QPushButton("＋ 항목 추가")
        add_item_btn.setProperty("small", True)
        add_item_btn.clicked.connect(self._add_item)
        items_header.addWidget(add_item_btn)
        del_item_btn = QPushButton("선택 항목 삭제")
        del_item_btn.setProperty("small", True)
        del_item_btn.setProperty("danger", True)
        del_item_btn.clicked.connect(self._delete_item)
        items_header.addWidget(del_item_btn)
        right.addLayout(items_header)

        self.item_list = QListWidget()
        self.item_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.item_list.model().rowsMoved.connect(self._on_rows_moved)
        right.addWidget(self.item_list, 1)

        # 선택된 항목 편집 폼
        self.item_form_frame = QFrame()
        self.item_form_frame.setProperty("card", True)
        form_layout = QVBoxLayout(self.item_form_frame)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(8)

        form_title = QLabel("선택한 항목 편집")
        form_title.setStyleSheet("font-weight: bold; border: none;")
        form_layout.addWidget(form_title)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("작업 설명"))
        self.item_desc_edit = QLineEdit()
        self.item_desc_edit.textEdited.connect(self._on_item_desc_edited)
        desc_row.addWidget(self.item_desc_edit, 1)
        form_layout.addLayout(desc_row)

        self.path_edits: dict[str, QLineEdit] = {}
        for code, country_name in COUNTRIES.items():
            row = QHBoxLayout()
            label = QLabel(country_name)
            label.setFixedWidth(58)
            row.addWidget(label)
            edit = QLineEdit()
            edit.setPlaceholderText(f"{country_name} 빌드의 파일/폴더 경로 (비워두면 경로 없음)")
            edit.textEdited.connect(
                lambda text, c=code: self._on_item_path_edited(c, text)
            )
            row.addWidget(edit, 1)
            file_btn = QPushButton("파일")
            file_btn.setProperty("small", True)
            file_btn.clicked.connect(lambda _, c=code: self._browse(c, folder=False))
            row.addWidget(file_btn)
            folder_btn = QPushButton("폴더")
            folder_btn.setProperty("small", True)
            folder_btn.clicked.connect(lambda _, c=code: self._browse(c, folder=True))
            row.addWidget(folder_btn)
            form_layout.addLayout(row)
            self.path_edits[code] = edit

        right.addWidget(self.item_form_frame)

        self.editor_host = QWidget()
        self.editor_host.setLayout(right)
        root.addWidget(self.editor_host, 1)

        self.empty_label = QLabel("프리셋을 선택하거나 [＋ 새 프리셋]으로 만들어보세요.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("muted", True)
        root.addWidget(self.empty_label, 1)

    # ---- 목록/선택 ----
    def refresh(self) -> None:
        self._loading = True
        selected = self.current_preset
        self.preset_list.clear()
        for preset in self.storage.presets:
            entry = QListWidgetItem(f"{preset.name}  ({len(preset.items)})")
            entry.setData(ITEM_ROLE, preset)
            self.preset_list.addItem(entry)
            if selected and preset.id == selected.id:
                self.preset_list.setCurrentItem(entry)
        self._loading = False
        if self.preset_list.currentItem() is None and self.preset_list.count():
            self.preset_list.setCurrentRow(0)
        else:
            self._load_editor()

    def _on_preset_selected(self, *_):
        if self._loading:
            return
        self._load_editor()

    def _load_editor(self) -> None:
        entry = self.preset_list.currentItem()
        self.current_preset = entry.data(ITEM_ROLE) if entry else None
        has_preset = self.current_preset is not None
        self.editor_host.setVisible(has_preset)
        self.empty_label.setVisible(not has_preset)
        if not has_preset:
            return

        self._loading = True
        preset = self.current_preset
        self.name_edit.setText(preset.name)
        self.desc_edit.setText(preset.description)
        self.item_list.clear()
        for item in preset.items:
            self._append_item_entry(item)
        self._loading = False
        if self.item_list.count():
            self.item_list.setCurrentRow(0)
        else:
            self._load_item_form()

    def _append_item_entry(self, item: PresetItem) -> QListWidgetItem:
        entry = QListWidgetItem(item.description or "(설명 없음)")
        entry.setData(ITEM_ROLE, item)
        self.item_list.addItem(entry)
        return entry

    def _on_item_selected(self, *_):
        if self._loading:
            return
        self._load_item_form()

    def _load_item_form(self) -> None:
        entry = self.item_list.currentItem()
        self.current_item = entry.data(ITEM_ROLE) if entry else None
        has_item = self.current_item is not None
        self.item_form_frame.setVisible(has_item)
        if not has_item:
            return
        self._loading = True
        self.item_desc_edit.setText(self.current_item.description)
        for code, edit in self.path_edits.items():
            edit.setText(self.current_item.paths.get(code, ""))
        self._loading = False

    # ---- 편집 동작 (모두 즉시 저장) ----
    def _on_meta_edited(self) -> None:
        if self._loading or not self.current_preset:
            return
        self.current_preset.name = self.name_edit.text().strip() or "이름 없는 프리셋"
        self.current_preset.description = self.desc_edit.text()
        entry = self.preset_list.currentItem()
        if entry:
            entry.setText(f"{self.current_preset.name}  ({len(self.current_preset.items)})")
        self.storage.save()
        self.presetsChanged.emit()

    def _on_item_desc_edited(self, text: str) -> None:
        if self._loading or not self.current_item:
            return
        self.current_item.description = text
        entry = self.item_list.currentItem()
        if entry:
            entry.setText(text or "(설명 없음)")
        self.storage.save()

    def _on_item_path_edited(self, code: str, text: str) -> None:
        if self._loading or not self.current_item:
            return
        self.current_item.paths[code] = text
        self.storage.save()

    def _browse(self, code: str, folder: bool) -> None:
        if folder:
            path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path and self.current_item:
            self.path_edits[code].setText(path)
            self.current_item.paths[code] = path
            self.storage.save()

    def _on_rows_moved(self, *_):
        if not self.current_preset:
            return
        self.current_preset.items = [
            self.item_list.item(i).data(ITEM_ROLE) for i in range(self.item_list.count())
        ]
        self.storage.save()

    def _add_item(self) -> None:
        if not self.current_preset:
            return
        item = PresetItem(description="새 작업")
        self.current_preset.items.append(item)
        entry = self._append_item_entry(item)
        self.item_list.setCurrentItem(entry)
        self.storage.save()
        self._update_current_count()
        self.item_desc_edit.setFocus()
        self.item_desc_edit.selectAll()

    def _delete_item(self) -> None:
        entry = self.item_list.currentItem()
        if not entry or not self.current_preset:
            return
        item = entry.data(ITEM_ROLE)
        self.current_preset.items.remove(item)
        self.item_list.takeItem(self.item_list.row(entry))
        self.storage.save()
        self._update_current_count()

    def _update_current_count(self) -> None:
        entry = self.preset_list.currentItem()
        if entry and self.current_preset:
            entry.setText(f"{self.current_preset.name}  ({len(self.current_preset.items)})")

    # ---- 프리셋 생성/삭제/입출력 ----
    def _create_preset(self) -> None:
        preset = Preset(name=self.storage.unique_preset_name("새 프리셋"))
        self.storage.presets.append(preset)
        self.storage.save()
        self.current_preset = preset
        self.refresh()
        self.presetsChanged.emit()
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _show_preset_menu(self, pos) -> None:
        entry = self.preset_list.itemAt(pos)
        if not entry:
            return
        preset = entry.data(ITEM_ROLE)
        menu = QMenu(self)
        delete_action = menu.addAction("삭제")
        if menu.exec(self.preset_list.mapToGlobal(pos)) == delete_action:
            answer = QMessageBox.question(
                self, "프리셋 삭제",
                f'"{preset.name}" 프리셋을 삭제할까요?\n'
                "(이미 생성된 체크리스트는 영향받지 않습니다)",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.storage.presets.remove(preset)
                if self.current_preset is preset:
                    self.current_preset = None
                self.storage.save()
                self.refresh()
                self.presetsChanged.emit()

    def _export_preset(self) -> None:
        entry = self.preset_list.currentItem()
        if not entry:
            QMessageBox.information(self, "내보내기", "내보낼 프리셋을 먼저 선택해주세요.")
            return
        preset: Preset = entry.data(ITEM_ROLE)
        path, _ = QFileDialog.getSaveFileName(
            self, "프리셋 내보내기", f"{preset.name}.json", "JSON 파일 (*.json)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(preset.to_dict(), f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "내보내기 완료", f"저장됨:\n{path}")

    def _import_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "프리셋 불러오기", "", "JSON 파일 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            preset = Preset.from_dict(data)
            preset.id = new_id()  # 외부 파일과의 id 충돌 방지
        except (json.JSONDecodeError, OSError, AttributeError, TypeError):
            QMessageBox.warning(self, "불러오기 실패", "올바른 프리셋 JSON 파일이 아닙니다.")
            return

        existing = self.storage.find_preset_by_name(preset.name)
        if existing:
            box = QMessageBox(self)
            box.setWindowTitle("같은 이름의 프리셋")
            box.setText(
                f'"{preset.name}" 프리셋이 이미 있습니다.\n어떻게 할까요?'
            )
            overwrite_btn = box.addButton("덮어쓰기", QMessageBox.ButtonRole.AcceptRole)
            rename_btn = box.addButton("새 이름으로 추가", QMessageBox.ButtonRole.ActionRole)
            box.addButton("취소", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == overwrite_btn:
                index = self.storage.presets.index(existing)
                preset.id = existing.id
                self.storage.presets[index] = preset
            elif box.clickedButton() == rename_btn:
                preset.name = self.storage.unique_preset_name(preset.name)
                self.storage.presets.append(preset)
            else:
                return
        else:
            self.storage.presets.append(preset)

        self.storage.save()
        self.current_preset = preset
        self.refresh()
        self.presetsChanged.emit()
        QMessageBox.information(
            self, "불러오기 완료",
            f'"{preset.name}" 프리셋을 불러왔습니다. (항목 {len(preset.items)}개)',
        )
