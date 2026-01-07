"""Shared GUI resources such as icons and paths."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ICON_PATH = PROJECT_ROOT / "Assets" / "app-icon.svg"
_APP_ICON_CACHE: Optional[QIcon] = None


def get_app_icon() -> QIcon:
    """Return the cached application icon, falling back to a theme icon."""

    global _APP_ICON_CACHE
    if _APP_ICON_CACHE is not None:
        return _APP_ICON_CACHE

    icon = QIcon()
    if APP_ICON_PATH.exists():
        icon = QIcon(str(APP_ICON_PATH))

    if icon.isNull():
        fallback = QIcon.fromTheme("applications-games")
        if not fallback.isNull():
            icon = fallback

    _APP_ICON_CACHE = icon
    return _APP_ICON_CACHE


__all__ = [
    "PROJECT_ROOT",
    "APP_ICON_PATH",
    "get_app_icon",
]
