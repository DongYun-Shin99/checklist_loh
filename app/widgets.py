"""공용 위젯 헬퍼."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel

from .models import COUNTRIES, COUNTRY_COLORS


def country_badge(code: str) -> QLabel:
    badge = QLabel(COUNTRIES.get(code, code))
    color = COUNTRY_COLORS.get(code, "#6b7280")
    badge.setStyleSheet(
        f"background: {color}; color: white; border-radius: 9px;"
        "padding: 2px 10px; font-size: 12px; font-weight: bold;"
    )
    return badge
