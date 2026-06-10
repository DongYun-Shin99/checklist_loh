"""메인 윈도우: 사이드바 + 페이지 전환 (패치 → 체크리스트 → 항목 3단계)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .pages.archive import ArchivePage
from .pages.checklist_detail import ChecklistDetailPage
from .pages.patch_detail import PatchDetailPage
from .pages.patches import PatchListPage
from .pages.presets import PresetPage
from .pages.resources import ResourcePage
from .storage import Storage


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.setWindowTitle("업무 체크리스트")
        self.resize(1100, 720)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        # ---- 사이드바 ----
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 12, 0, 0)
        side_layout.setSpacing(2)

        self.nav_group = QButtonGroup(self)
        self.nav_buttons: list[QPushButton] = []
        for index, label in enumerate(["패치", "프리셋", "리소스 경로", "보관함"]):
            btn = QPushButton(label)
            btn.setProperty("sidebar", True)
            btn.setCheckable(True)
            self.nav_group.addButton(btn, index)
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        side_layout.addStretch()
        root.addWidget(sidebar)

        # ---- 페이지 ----
        self.stack = QStackedWidget()
        self.patch_list_page = PatchListPage(storage)
        self.patch_detail_page = PatchDetailPage(storage)
        self.checklist_detail_page = ChecklistDetailPage(storage)
        self.preset_page = PresetPage(storage)
        self.resource_page = ResourcePage(storage)
        self.archive_page = ArchivePage(storage)
        for page in (
            self.patch_list_page,
            self.patch_detail_page,
            self.checklist_detail_page,
            self.preset_page,
            self.resource_page,
            self.archive_page,
        ):
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        # ---- 연결 ----
        self.nav_group.idClicked.connect(self._on_nav)
        self.patch_list_page.openRequested.connect(self._open_patch)
        self.patch_list_page.dataChanged.connect(self.archive_page.refresh)
        self.patch_detail_page.backRequested.connect(self._back_to_patch_list)
        self.patch_detail_page.openChecklistRequested.connect(self._open_checklist)
        self.patch_detail_page.archivedChanged.connect(self.archive_page.refresh)
        self.checklist_detail_page.backRequested.connect(self._back_to_patch_detail)
        self.checklist_detail_page.checklistCompleted.connect(self._on_checklist_completed)
        self.archive_page.restored.connect(self.patch_list_page.refresh)

        self.nav_buttons[0].setChecked(True)
        self._on_nav(0)

    def _on_nav(self, index: int) -> None:
        pages = [self.patch_list_page, self.preset_page, self.resource_page, self.archive_page]
        page = pages[index]
        page.refresh()
        self.stack.setCurrentWidget(page)

    # ---- 3단계 네비게이션 ----
    def _open_patch(self, patch_id: str) -> None:
        patch = self.storage.find_patch(patch_id)
        if not patch:
            return
        self.patch_detail_page.set_patch(patch)
        self.stack.setCurrentWidget(self.patch_detail_page)

    def _open_checklist(self, checklist_id: str) -> None:
        patch, checklist = self.storage.find_checklist(checklist_id)
        if not checklist:
            return
        self.checklist_detail_page.set_checklist(patch, checklist)
        self.stack.setCurrentWidget(self.checklist_detail_page)

    def _back_to_patch_list(self) -> None:
        self.patch_list_page.refresh()
        self.stack.setCurrentWidget(self.patch_list_page)
        self.nav_buttons[0].setChecked(True)

    def _back_to_patch_detail(self) -> None:
        self.patch_detail_page.refresh()
        self.stack.setCurrentWidget(self.patch_detail_page)

    def _on_checklist_completed(self) -> None:
        """체크리스트의 마지막 항목 완료 → 패치 전체 완료면 보관 여부 확인."""
        patch = self.checklist_detail_page.patch
        if patch and patch.is_done and not patch.is_archived:
            self.patch_detail_page.set_patch(patch)
            if self.patch_detail_page.maybe_archive_patch():
                self._back_to_patch_list()
