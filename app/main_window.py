"""메인 윈도우: 사이드바 + 페이지 전환."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .pages.archive import ArchivePage
from .pages.checklist_detail import ChecklistDetailPage
from .pages.checklists import ChecklistListPage
from .pages.presets import PresetPage
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
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(2)
        app_title = QLabel("✓ 업무 체크리스트")
        app_title.setObjectName("SidebarTitle")
        side_layout.addWidget(app_title)

        self.nav_group = QButtonGroup(self)
        self.nav_buttons: list[QPushButton] = []
        for index, label in enumerate(["체크리스트", "프리셋", "보관함"]):
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
        self.list_page = ChecklistListPage(storage)
        self.detail_page = ChecklistDetailPage(storage)
        self.preset_page = PresetPage(storage)
        self.archive_page = ArchivePage(storage)
        for page in (self.list_page, self.detail_page, self.preset_page, self.archive_page):
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        # ---- 연결 ----
        self.nav_group.idClicked.connect(self._on_nav)
        self.list_page.openRequested.connect(self._open_detail)
        self.list_page.dataChanged.connect(self.archive_page.refresh)
        self.detail_page.backRequested.connect(self._back_to_list)
        self.detail_page.archivedChanged.connect(self.archive_page.refresh)
        self.archive_page.restored.connect(self.list_page.refresh)

        self.nav_buttons[0].setChecked(True)
        self._on_nav(0)

    def _on_nav(self, index: int) -> None:
        pages = [self.list_page, self.preset_page, self.archive_page]
        page = pages[index]
        page.refresh()
        self.stack.setCurrentWidget(page)

    def _open_detail(self, checklist_id: str) -> None:
        checklist = self.storage.find_checklist(checklist_id)
        if not checklist:
            return
        self.detail_page.set_checklist(checklist)
        self.stack.setCurrentWidget(self.detail_page)

    def _back_to_list(self) -> None:
        self.list_page.refresh()
        self.stack.setCurrentWidget(self.list_page)
        self.nav_buttons[0].setChecked(True)
