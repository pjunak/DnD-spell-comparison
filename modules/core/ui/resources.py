"""Shared GUI resources such as icons and paths."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon

import sys

def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    # modules/core/ui/resources.py -> up 3 levels to modules, 4 to root
    return Path(__file__).resolve().parents[3]

PROJECT_ROOT = _get_project_root()
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
