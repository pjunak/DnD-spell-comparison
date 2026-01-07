"""Centralized UI theme definitions for Living Scroll.

This module exports the main stylesheet and color palette constants.
Modify this file to update the look and feel of the entire application.
"""

from __future__ import annotations

# --- Color Palette (VSCode-like Dark/Modern) ---
COLORS = {
    # Base
    "bg_main": "#1e1e1e",
    "bg_secondary": "#252526",
    "bg_tertiary": "#2d2d30",
    "bg_input": "#2b2b2b",  # Matches Bestiary/Grimoire input background
    
    # Text
    "text_primary": "#cccccc",
    "text_secondary": "#999999",
    "text_bright": "#ffffff",
    
    # Accents
    "accent_primary": "#9b59b6", # Purple (User preferred)
    "accent_primary_hover": "#8e44ad",
    "accent_hover": "#4e4e4e",
    "accent_red": "#e74c3c",
    "accent_green": "#27ae60",
    
    # Borders
    "border_dim": "#3e3e42",
    "border_input": "#5d5d5d",
    "border_checkbox": "#888888", # Lighter border for visibility
    "border_focus": "#9b59b6",
}

# --- Style Components ---

_CORE_STYLES = f"""
/* Main Window & Backgrounds */
QMainWindow, QWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_primary']};
    font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10pt;
}}

/* Groups & Frames */
QGroupBox {{
    border: 1px solid {COLORS['border_dim']};
    border-radius: 4px;
    margin-top: 1.2em;
    padding-top: 10px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: {COLORS['text_primary']};
}}

/* Header Labels */
QLabel[class="HeaderLabel"] {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['accent_primary']};
}}
"""

_INPUT_STYLES = f"""
/* Inputs & Buttons */
QLineEdit, QComboBox, QSpinBox {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border_input']};
    border-radius: 4px;
    padding: 4px 8px;
    color: {COLORS['text_bright']};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {COLORS['border_focus']};
}}

QPushButton, QToolButton {{
    background-color: {COLORS['bg_input']}; 
    border: 1px solid {COLORS['border_dim']};
    border-radius: 4px;
    padding: 5px 10px;
    color: {COLORS['text_primary']};
}}

QPushButton:hover, QToolButton:hover {{
    background-color: {COLORS['accent_hover']};
    border: 1px solid {COLORS['accent_primary']};
}}

QPushButton:pressed, QToolButton:pressed {{
    background-color: {COLORS['accent_primary']};
    color: {COLORS['text_bright']};
}}

/* Primary Action Button */
QPushButton[class="PrimaryButton"] {{
    background-color: {COLORS['accent_primary']};
    color: {COLORS['text_bright']};
    font-weight: bold;
    border: none;
}}

QPushButton[class="PrimaryButton"]:hover {{
    background-color: {COLORS['accent_primary_hover']};
}}

QPushButton[class="PrimaryButton"]:disabled {{
    background-color: #2c3e50;
    color: #7f8c8d;
}}

/* Filter/Toggle Buttons (Checked State) */
QPushButton:checked, QToolButton:checked {{
    background-color: {COLORS['accent_primary']};
    color: {COLORS['text_bright']};
    border: 1px solid {COLORS['accent_primary']};
}}

/* ComboBox Specifics */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 0px;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
}}

QComboBox::down-arrow {{
    width: 0; 
    height: 0; 
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLORS['text_primary']};
    margin-right: 8px;
}}

/* Dropdown list styling */
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border_dim']};
    selection-background-color: {COLORS['accent_primary']};
    selection-color: {COLORS['text_bright']};
    outline: none;
}}
"""

_CHECKBOX_STYLES = f"""
/* Checkboxes & Radio Buttons */
QCheckBox {{
    spacing: 8px;
    color: {COLORS['text_primary']};
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border_checkbox']}; /* Lighter border */
    border-radius: 2px;
    background: {COLORS['bg_input']};
    margin: 1px;
}}

QCheckBox::indicator:unchecked:hover {{
    border-color: {COLORS['accent_primary']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-32.png); 
}}

QCheckBox::indicator:checked:hover {{
    background-color: {COLORS['accent_primary_hover']};
    border-color: {COLORS['accent_primary_hover']};
}}

QRadioButton {{
    spacing: 8px;
    color: {COLORS['text_primary']};
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border_checkbox']};
    border-radius: 8px; /* Round */
    background: {COLORS['bg_input']};
}}
QRadioButton::indicator:checked {{
    background-color: {COLORS['accent_primary']};
    border: 4px solid {COLORS['bg_input']}; /* Creates a 'dot' effect */
}}
"""

_SCROLL_LIST_STYLES = f"""
/* Lists, Trees, Tables */
QListWidget, QTreeWidget, QTableView, QTableWidget, QTextBrowser, QScrollArea {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border_dim']};
    border-radius: 2px;
    outline: none;
}}

QListWidget::item, QTreeWidget::item {{
    padding: 6px;
    border-radius: 2px;
}}

QListWidget::item:hover, QTreeWidget::item:hover, QTableView::item:hover, QTableWidget::item:hover {{
    background-color: {COLORS['accent_primary']}40; /* 25% opacity accent */
}}

QListWidget::item:selected, QTreeWidget::item:selected, QTableView::item:selected, QTableWidget::item:selected {{
    background-color: {COLORS['accent_primary']};
    color: {COLORS['text_bright']};
}}

/* Headers */
QHeaderView::section {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {COLORS['border_dim']};
    border-right: 1px solid {COLORS['border_dim']};
    font-weight: bold;
}}

/* Indicators (Checkboxes inside lists) */
QListWidget::indicator, QTreeWidget::indicator, QTableView::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border_checkbox']};
    border-radius: 2px;
    background: {COLORS['bg_input']};
    margin-right: 4px;
}}

QListWidget::indicator:unchecked:hover, QTreeWidget::indicator:unchecked:hover {{
    border-color: {COLORS['accent_primary']};
}}

QListWidget::indicator:checked, QTreeWidget::indicator:checked {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-32.png);
}}

QListWidget::indicator:checked:hover, QTreeWidget::indicator:checked:hover {{
    background-color: {COLORS['accent_primary_hover']};
    border-color: {COLORS['accent_primary_hover']};
}}
"""

_SCROLLBAR_STYLES = f"""
/* Scrollbars */
QScrollBar:vertical {{
    background: {COLORS['bg_main']};
    width: 12px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #424242;
    min-height: 20px;
    border-radius: 6px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: #4f4f4f;
}}

QScrollBar:horizontal {{
    background: {COLORS['bg_main']};
    height: 12px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: #424242;
    min-width: 20px;
    border-radius: 6px;
    margin: 2px;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px; height: 0px;
}}
"""

_TAB_STYLES = f"""
/* TabWidget */
QTabWidget::pane {{
    border: 1px solid {COLORS['border_dim']};
    background-color: {COLORS['bg_main']};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    padding: 8px 16px;
    border: 1px solid {COLORS['border_dim']};
    border-bottom: none;
    margin-right: 2px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_main']};
    border-bottom: 1px solid {COLORS['bg_main']};
    color: {COLORS['accent_primary']}; /* Purple text for selected tab */
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_input']};
}}
"""

_CUSTOM_WIDGET_STYLES = f"""
/* Custom Title Bar */
QWidget#CustomTitleBar {{
    background-color: {COLORS['bg_secondary']};
    border-bottom: 2px solid {COLORS['accent_primary']}; /* Purple Line under title bar */
}}

QLabel#TitleBarLabel {{
    color: {COLORS['text_primary']};
    font-weight: bold;
    border: none;
}}

/* Window Control Buttons */
QPushButton[class="TitleBarButton"], QPushButton[class="TitleBarCloseButton"] {{
    background-color: transparent;
    border: none;
    color: {COLORS['text_primary']};
    border-radius: 0;
}}

QPushButton[class="TitleBarButton"]:hover {{
    background-color: {COLORS['bg_input']};
}}

QPushButton[class="TitleBarCloseButton"]:hover {{
    background-color: {COLORS['accent_red']};
    color: {COLORS['text_bright']};
}}

/* Launcher Tiles */
QPushButton[class="TileButton"] {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_dim']};
    border-radius: 6px;
    text-align: left;
    padding: 20px;
    font-size: 18px;
    font-weight: 600;
}}

QPushButton[class="TileButton"]:hover {{
    background-color: {COLORS['bg_tertiary']};
    border: 1px solid {COLORS['accent_primary']}; /* Purple border on hover */
}}

QPushButton[class="TileButton"]:pressed {{
    background-color: {COLORS['accent_primary']};
    color: {COLORS['text_bright']};
}}

/* Character Tile (Selector) */
QFrame[class="CharacterTile"] {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border_dim']};
    border-radius: 12px;
}}
QFrame[class="CharacterTile"]:hover {{
    background-color: {COLORS['bg_tertiary']};
    border-color: {COLORS['accent_primary']};
}}
QFrame[class="CharacterTile"][isSelected="true"] {{
    border: 2px solid {COLORS['accent_primary']};
    background-color: {COLORS['bg_main']};
}}

/* Character Portrait */
QLabel[class="CharacterPortrait"] {{
    background-color: {COLORS['bg_tertiary']};
    border: 2px solid {COLORS['border_dim']};
    border-radius: 8px; /* Slightly rounded squares */
}}
QLabel[class="CharacterPortrait"]:hover {{
    border-color: {COLORS['accent_primary']};
}}
"""

# Combine all blocks
DARK_THEME_STYLESHEET = "\n".join([
    _CORE_STYLES,
    _INPUT_STYLES,
    _CHECKBOX_STYLES,
    _SCROLL_LIST_STYLES,
    _SCROLLBAR_STYLES,
    _TAB_STYLES,
    _CUSTOM_WIDGET_STYLES
])

__all__ = ["DARK_THEME_STYLESHEET", "COLORS"]
