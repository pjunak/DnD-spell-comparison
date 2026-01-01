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

DARK_THEME_STYLESHEET = """
/* Main Window & Backgrounds */
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10pt;
}

/* Inputs & Buttons */
QLineEdit, QComboBox, QPushButton, QToolButton {
    background-color: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 2px;
    padding: 4px 8px;
    color: #cccccc;
}

QLineEdit:focus, QComboBox:focus, QPushButton:focus, QToolButton:focus {
    border: 1px solid #007acc;
}

QPushButton:hover, QToolButton:hover {
    background-color: #4e4e4e;
}

QPushButton:pressed, QToolButton:pressed {
    background-color: #007acc;
    color: white;
}

QPushButton:checked, QToolButton:checked {
    background-color: #007acc;
    color: white;
    border: 1px solid #007acc;
}

/* ComboBox Specifics */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 0px;
    border-top-right-radius: 2px;
    border-bottom-right-radius: 2px;
}

QComboBox::down-arrow {
    width: 0; 
    height: 0; 
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #cccccc;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #252526;
    border: 1px solid #3e3e42;
    selection-background-color: #094771;
    selection-color: white;
    outline: none;
}

/* Lists, Trees, Tables */
QListWidget, QTreeWidget, QTableView, QTableWidget, QTextBrowser {
    background-color: #252526;
    border: 1px solid #3e3e42;
    border-radius: 2px;
    outline: none;
}

QHeaderView::section {
    background-color: #252526;
    color: #cccccc;
    padding: 4px;
    border: none;
    border-bottom: 1px solid #3e3e42;
    border-right: 1px solid #3e3e42;
}

QHeaderView::section:hover {
    background-color: #3e3e42;
}

QTableView, QTableWidget {
    gridline-color: #3e3e42;
    selection-background-color: #094771;
    selection-color: white;
}

QTableView::item, QTableWidget::item {
    padding: 4px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #1e1e1e;
    width: 14px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #424242;
    min-height: 20px;
    border-radius: 0px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #4f4f4f;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #1e1e1e;
    height: 14px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #424242;
    min-width: 20px;
    border-radius: 0px;
    margin: 2px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Splitter */
QSplitter::handle {
    background-color: #1e1e1e;
}

/* Menus */
QMenuBar {
    background-color: #1e1e1e;
    color: #cccccc;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}

QMenuBar::item:selected {
    background-color: #3e3e42;
}

QMenu {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
}

QMenu::item {
    padding: 4px 24px 4px 8px;
}

QMenu::item:selected {
    background-color: #094771;
    color: white;
}

/* Tooltips */
QToolTip {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    padding: 4px;
}

/* GroupBox */
QGroupBox {
    border: 1px solid #3e3e42;
    border-radius: 2px;
    margin-top: 1em;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 3px;
    color: #cccccc;
}

/* TabWidget */
QTabWidget::pane {
    border: 1px solid #3e3e42;
    background-color: #1e1e1e;
}

QTabBar::tab {
    background-color: #2d2d30;
    color: #cccccc;
    padding: 6px 12px;
    border: 1px solid #3e3e42;
    border-bottom: none;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 1px solid #1e1e1e; /* Blend with pane */
}

QTabBar::tab:hover:!selected {
    background-color: #3e3e42;
}

/* Launcher Tiles */
QPushButton[class="TileButton"] {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    text-align: left;
    padding: 20px;
    font-size: 18px;
    font-weight: 600;
}

QPushButton[class="TileButton"]:hover {
    background-color: #2d2d30;
    border: 1px solid #007acc;
}

QPushButton[class="TileButton"]:pressed {
    background-color: #007acc;
    color: white;
}

/* Custom Title Bar */
QWidget#CustomTitleBar {
    background-color: #252526;
    border-bottom: 1px solid #3e3e42;
}

QLabel#TitleBarLabel {
    color: #cccccc;
    font-weight: bold;
    border: none;
}

QPushButton[class="TitleBarButton"] {
    background-color: transparent;
    border: none;
    color: #cccccc;
    font-family: "Segoe UI Symbol", "Arial";
    font-size: 14px;
    min-width: 46px;
    max-width: 46px;
    min-height: 32px;
    max-height: 32px;
    border-radius: 0px;
}

QPushButton[class="TitleBarButton"]:hover {
    background-color: #3e3e42;
}

QPushButton[class="TitleBarCloseButton"] {
    background-color: transparent;
    border: none;
    color: #cccccc;
    font-family: "Segoe UI Symbol", "Arial";
    font-size: 14px;
    min-width: 46px;
    max-width: 46px;
    min-height: 32px;
    max-height: 32px;
    border-radius: 0px;
}

QPushButton[class="TitleBarCloseButton"]:hover {
    background-color: #e81123;
    color: white;
}
"""
