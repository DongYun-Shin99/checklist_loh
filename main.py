"""업무 체크리스트 프로그램 진입점.

실행:  python main.py
빌드:  pyinstaller --onefile --windowed --name checklist main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.storage import Storage
from app.style import STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    storage = Storage()
    window = MainWindow(storage)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
