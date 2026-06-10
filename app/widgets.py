"""공용 위젯 헬퍼."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel

from .models import COUNTRY_COLORS, Checklist


def country_badge(checklist: Checklist) -> QLabel:
    badge = QLabel(checklist.country_name)
    color = COUNTRY_COLORS.get(checklist.country, "#6b7280")
    badge.setStyleSheet(
        f"background: {color}; color: white; border-radius: 9px;"
        "padding: 2px 10px; font-size: 12px; font-weight: bold;"
    )
    return badge
