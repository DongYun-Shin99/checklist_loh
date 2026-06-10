"""앱 전체 QSS 스타일시트 (라이트 테마, 파랑 포인트)."""

ACCENT = "#2563eb"

STYLESHEET = """
* {
    font-family: "Malgun Gothic", "맑은 고딕", "Noto Sans CJK KR", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #f3f4f6;
}

/* ---- 사이드바 ---- */
#Sidebar {
    background: #1f2937;
    min-width: 168px;
    max-width: 168px;
}
#SidebarTitle {
    color: #f9fafb;
    font-size: 16px;
    font-weight: bold;
    padding: 20px 16px 14px 16px;
}
QPushButton[sidebar="true"] {
    color: #d1d5db;
    background: transparent;
    border: none;
    text-align: left;
    padding: 11px 18px;
    font-size: 14px;
    border-radius: 0;
}
QPushButton[sidebar="true"]:hover {
    background: #374151;
    color: white;
}
QPushButton[sidebar="true"]:checked {
    background: #2563eb;
    color: white;
    font-weight: bold;
}

/* ---- 카드 ---- */
QFrame[card="true"] {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}
QFrame[card="true"]:hover {
    border: 1px solid #2563eb;
}

/* ---- 버튼 ---- */
QPushButton {
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton:hover {
    background: #f9fafb;
    border-color: #9ca3af;
}
QPushButton:disabled {
    color: #9ca3af;
    background: #f3f4f6;
}
QPushButton[primary="true"] {
    background: #2563eb;
    color: white;
    border: none;
    font-weight: bold;
    padding: 7px 16px;
}
QPushButton[primary="true"]:hover {
    background: #1d4ed8;
}
QPushButton[danger="true"] {
    color: #dc2626;
}
QPushButton[small="true"] {
    padding: 3px 9px;
    font-size: 12px;
}

/* ---- 입력 ---- */
QLineEdit, QDateEdit, QComboBox {
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 9px;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #2563eb;
}
QLineEdit[flat="true"] {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    color: #6b7280;
}
QLineEdit[flat="true"]:hover, QLineEdit[flat="true"]:focus {
    background: #f3f4f6;
}

/* ---- 목록/트리 ---- */
QListWidget, QTreeWidget {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QListWidget::item, QTreeWidget::item {
    padding: 7px 8px;
    border-radius: 6px;
    color: #111827;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #dbeafe;
    color: #1e40af;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background: #f3f4f6;
}
QHeaderView::section {
    background: #f9fafb;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 6px 8px;
    font-weight: bold;
    color: #374151;
}

/* ---- 진행률 바 ---- */
QProgressBar {
    background: #e5e7eb;
    border: none;
    border-radius: 4px;
    max-height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 4px;
}

/* ---- 체크박스 ---- */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #d1d5db;
    border-radius: 5px;
    background: white;
}
QCheckBox::indicator:hover {
    border-color: #2563eb;
}
QCheckBox::indicator:checked {
    background: #2563eb;
    border-color: #2563eb;
    image: url(none);
}

QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLabel[h1="true"] {
    font-size: 19px;
    font-weight: bold;
    color: #111827;
}
QLabel[muted="true"] {
    color: #6b7280;
}
QTextBrowser {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
"""
