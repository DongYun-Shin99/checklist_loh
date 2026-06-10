"""공용 유틸: D-day 계산, 탐색기 열기."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

COLOR_MUTED = "#6b7280"
COLOR_WARN = "#d97706"
COLOR_DANGER = "#dc2626"


def dday_info(due_date: str) -> tuple[str, str]:
    """기한 문자열(YYYY-MM-DD) → (표시 텍스트, 색상)."""
    if not due_date:
        return "기한 없음", COLOR_MUTED
    try:
        due = date.fromisoformat(due_date)
    except ValueError:
        return "기한 없음", COLOR_MUTED
    diff = (due - date.today()).days
    if diff > 3:
        return f"D-{diff}", COLOR_MUTED
    if diff > 0:
        return f"D-{diff}", COLOR_WARN
    if diff == 0:
        return "D-DAY", COLOR_WARN
    return f"D+{-diff}", COLOR_DANGER


def open_in_explorer(path: str) -> None:
    """파일이면 탐색기에서 해당 파일을 선택한 채로, 폴더면 폴더를 연다."""
    p = Path(path)
    if sys.platform == "win32":
        if p.is_file():
            subprocess.Popen(["explorer", "/select,", os.path.normpath(str(p))])
        else:
            os.startfile(str(p))  # noqa: S606 - 사용자가 등록한 경로 열기
    else:
        target = p if p.is_dir() else p.parent
        subprocess.Popen(["xdg-open", str(target)])
