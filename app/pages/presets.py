"""프리셋 관리 화면: 목록 + 편집기(하위 항목 지원), 내보내기/불러오기."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
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
        items_label = QLabel("항목")
        items_label.setProperty("muted", True)
        items_header.addWidget(items_label)
        items_header.addStretch()
        add_item_btn = QPushButton("＋ 항목 추가")
        add_item_btn.setProperty("small", True)
        add_item_btn.clicked.connect(self._add_item)
        items_header.addWidget(add_item_btn)
        add_child_btn = QPushButton("＋ 하위 항목")
        add_child_btn.setProperty("small", True)
        add_child_btn.clicked.connect(self._add_child_item)
        items_header.addWidget(add_child_btn)
        up_btn = QPushButton("↑")
        up_btn.setProperty("small", True)
        up_btn.clicked.connect(lambda: self._move_item(-1))
        items_header.addWidget(up_btn)
        down_btn = QPushButton("↓")
        down_btn.setProperty("small", True)
        down_btn.clicked.connect(lambda: self._move_item(1))
        items_header.addWidget(down_btn)
        del_item_btn = QPushButton("삭제")
        del_item_btn.setProperty("small", True)
        del_item_btn.setProperty("danger", True)
        del_item_btn.clicked.connect(self._delete_item)
        items_header.addWidget(del_item_btn)
        right.addLayout(items_header)

        self.item_tree = QTreeWidget()
        self.item_tree.setHeaderHidden(True)
        self.item_tree.currentItemChanged.connect(self._on_item_selected)
        right.addWidget(self.item_tree, 1)

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

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel(""), 0, 0)
        folder_header = QLabel("폴더 경로")
        folder_header.setProperty("muted", True)
        grid.addWidget(folder_header, 0, 1)
        file_header = QLabel("파일 명")
        file_header.setProperty("muted", True)
        grid.addWidget(file_header, 0, 3)

        self.folder_edits: dict[str, QLineEdit] = {}
        self.file_edits: dict[str, QLineEdit] = {}
        for row, (code, country_name) in enumerate(COUNTRIES.items(), start=1):
            label = QLabel(country_name)
            label.setFixedWidth(40)
            grid.addWidget(label, row, 0)

            folder_edit = QLineEdit()
            folder_edit.setPlaceholderText("폴더 경로 (비워두면 없음)")
            folder_edit.textEdited.connect(
                lambda text, c=code: self._on_item_path_edited(c, "folder", text)
            )
            grid.addWidget(folder_edit, row, 1)
            folder_btn = QPushButton("폴더")
            folder_btn.setProperty("small", True)
            folder_btn.clicked.connect(lambda _, c=code: self._browse_folder(c))
            grid.addWidget(folder_btn, row, 2)

            file_edit = QLineEdit()
            file_edit.setPlaceholderText("파일 명 (선택)")
            file_edit.textEdited.connect(
                lambda text, c=code: self._on_item_path_edited(c, "file", text)
            )
            grid.addWidget(file_edit, row, 3)
            file_btn = QPushButton("파일")
            file_btn.setProperty("small", True)
            file_btn.clicked.connect(lambda _, c=code: self._browse_file(c))
            grid.addWidget(file_btn, row, 4)

            self.folder_edits[code] = folder_edit
            self.file_edits[code] = file_edit
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(3, 2)
        form_layout.addLayout(grid)

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
        self._rebuild_tree()
        self._loading = False
        if self.item_tree.topLevelItemCount():
            self.item_tree.setCurrentItem(self.item_tree.topLevelItem(0))
        else:
            self._load_item_form()

    def _rebuild_tree(self, select_item: PresetItem | None = None) -> None:
        was_loading = self._loading
        self._loading = True
        self.item_tree.clear()
        to_select = None
        for item in self.current_preset.items:
            node = QTreeWidgetItem([item.description or "(설명 없음)"])
            node.setData(0, ITEM_ROLE, item)
            self.item_tree.addTopLevelItem(node)
            if item is select_item:
                to_select = node
            for child in item.children:
                child_node = QTreeWidgetItem([child.description or "(설명 없음)"])
                child_node.setData(0, ITEM_ROLE, child)
                node.addChild(child_node)
                if child is select_item:
                    to_select = child_node
            node.setExpanded(True)
        self._loading = was_loading
        if to_select:
            self.item_tree.setCurrentItem(to_select)

    def _on_item_selected(self, *_):
        if self._loading:
            return
        self._load_item_form()

    def _load_item_form(self) -> None:
        node = self.item_tree.currentItem()
        self.current_item = node.data(0, ITEM_ROLE) if node else None
        has_item = self.current_item is not None
        self.item_form_frame.setVisible(has_item)
        if not has_item:
            return
        self._loading = True
        self.item_desc_edit.setText(self.current_item.description)
        for code in COUNTRIES:
            path = self.current_item.paths.get(code, {})
            self.folder_edits[code].setText(path.get("folder", ""))
            self.file_edits[code].setText(path.get("file", ""))
        self._loading = False

    # ---- 항목 트리 헬퍼 ----
    def _find_parent_list(self, item: PresetItem) -> list | None:
        """항목이 속한 리스트(최상위 또는 부모의 children)를 찾는다."""
        if item in self.current_preset.items:
            return self.current_preset.items
        for top in self.current_preset.items:
            if item in top.children:
                return top.children
        return None

    # ---- 편집 동작 (모두 즉시 저장) ----
    def _on_meta_edited(self) -> None:
        if self._loading or not self.current_preset:
            return
        self.current_preset.name = self.name_edit.text().strip() or "이름 없는 프리셋"
        self.current_preset.description = self.desc_edit.text()
        self._update_current_count()
        self.storage.save()
        self.presetsChanged.emit()

    def _on_item_desc_edited(self, text: str) -> None:
        if self._loading or not self.current_item:
            return
        self.current_item.description = text
        node = self.item_tree.currentItem()
        if node:
            node.setText(0, text or "(설명 없음)")
        self.storage.save()

    def _on_item_path_edited(self, code: str, key: str, text: str) -> None:
        if self._loading or not self.current_item:
            return
        self.current_item.paths.setdefault(code, {"folder": "", "file": ""})[key] = text
        self.storage.save()

    def _browse_folder(self, code: str) -> None:
        path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if path and self.current_item:
            self.folder_edits[code].setText(path)
            self.current_item.paths.setdefault(code, {})["folder"] = path
            self.storage.save()

    def _browse_file(self, code: str) -> None:
        """파일을 고르면 폴더/파일 칸이 자동으로 나뉘어 채워진다."""
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path and self.current_item:
            from pathlib import Path

            p = Path(path)
            self.folder_edits[code].setText(str(p.parent))
            self.file_edits[code].setText(p.name)
            entry = self.current_item.paths.setdefault(code, {})
            entry["folder"] = str(p.parent)
            entry["file"] = p.name
            self.storage.save()

    def _add_item(self) -> None:
        if not self.current_preset:
            return
        item = PresetItem(description="새 작업")
        self.current_preset.items.append(item)
        self.storage.save()
        self._rebuild_tree(select_item=item)
        self._update_current_count()
        self.item_desc_edit.setFocus()
        self.item_desc_edit.selectAll()

    def _add_child_item(self) -> None:
        if not self.current_preset or not self.current_item:
            QMessageBox.information(self, "하위 항목", "먼저 상위 항목을 선택해주세요.")
            return
        parent = self.current_item
        # 선택된 게 하위 항목이면 그 부모 밑에 추가 (깊이 1단계 제한)
        if parent not in self.current_preset.items:
            for top in self.current_preset.items:
                if parent in top.children:
                    parent = top
                    break
        child = PresetItem(description="새 하위 작업")
        parent.children.append(child)
        self.storage.save()
        self._rebuild_tree(select_item=child)
        self.item_desc_edit.setFocus()
        self.item_desc_edit.selectAll()

    def _move_item(self, delta: int) -> None:
        if not self.current_item:
            return
        siblings = self._find_parent_list(self.current_item)
        if siblings is None:
            return
        index = siblings.index(self.current_item)
        new_index = index + delta
        if not 0 <= new_index < len(siblings):
            return
        siblings[index], siblings[new_index] = siblings[new_index], siblings[index]
        self.storage.save()
        self._rebuild_tree(select_item=self.current_item)

    def _delete_item(self) -> None:
        if not self.current_item or not self.current_preset:
            return
        item = self.current_item
        if item.children:
            answer = QMessageBox.question(
                self, "항목 삭제", "하위 항목도 함께 삭제됩니다. 삭제할까요?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        siblings = self._find_parent_list(item)
        if siblings is None:
            return
        siblings.remove(item)
        self.current_item = None
        self.storage.save()
        self._rebuild_tree()
        self._update_current_count()
        self._load_item_form()

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
