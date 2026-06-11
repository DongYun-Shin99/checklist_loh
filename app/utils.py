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


# ---- 윈도우 시작 시 자동 실행 (레지스트리 Run 키) ----
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "ChecklistLOH"


def autostart_available() -> bool:
    """exe로 패키징된 윈도우 빌드에서만 자동 실행 등록 가능."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def get_autostart() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> bool:
    """현재 실행 중인 exe를 윈도우 시작 프로그램에 등록/해제."""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{sys.executable}"'
                )
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def combined_path(folder: str, file: str) -> str:
    """폴더 + 파일명을 합친 전체 경로. 파일이 없으면 폴더만."""
    if folder and file:
        return os.path.join(folder, file)
    return folder or file


def strip_base(path: str, base_paths: dict) -> str:
    """절대 경로가 기본 폴더 아래면 상대 경로로 줄여준다. 아니면 그대로."""
    normalized = path.replace("\\", "/").rstrip("/").lower()
    for base in base_paths.values():
        if not base:
            continue
        base_norm = base.replace("\\", "/").rstrip("/").lower()
        if normalized == base_norm:
            return ""
        if normalized.startswith(base_norm + "/"):
            return path[len(base):].strip("/\\")
    return path


def path_display(folder: str, file: str) -> str:
    """항목 행에 표시할 경로 텍스트."""
    parts = []
    if folder:
        parts.append(f"📁 {folder}")
    if file:
        parts.append(f"📄 {file}")
    return "   ".join(parts)
