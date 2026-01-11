"""Launcher window presenting module tiles for the Living Scroll suite."""

from __future__ import annotations

from typing import List
import logging

from PySide6.QtCore import Qt, QRectF, QSize, QPointF
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QPainterPath, QIcon, QAction
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QToolButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
    QMenu,
    QApplication,
)

from modules.core.application_context import ApplicationContext
from modules.core.ui.dialogs import GlobalSettingsDialog
from modules.core.ui.resources import get_app_icon
from modules.core.ui.widgets import FramelessWindow

# Window classes are imported lazily in handler methods to improve startup time


def _create_tile_icon(kind: str, size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    if kind == "graph":
        # Magical Diagram (Pentagram-ish graph)
        painter.setPen(QPen(QColor("#8E44AD"), 2)) # Mystical Purple
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Outer circle
        painter.drawEllipse(10, 10, 44, 44)
        
        # Inner star/graph lines
        path = QPainterPath()
        path.moveTo(32, 10)
        path.lineTo(45, 45)
        path.lineTo(15, 25)
        path.lineTo(49, 25)
        path.lineTo(19, 45)
        path.closeSubpath()
        painter.drawPath(path)
        
        # Nodes
        painter.setBrush(QColor("#9B59B6"))
        painter.setPen(Qt.PenStyle.NoPen)
        for x, y in [(32, 10), (45, 45), (15, 25), (49, 25), (19, 45)]:
            painter.drawEllipse(QPointF(x, y), 3, 3)
        
    elif kind == "silhouette":
        # Hooded Figure Silhouette
        painter.setBrush(QColor("#34495E")) # Dark Blue-Grey
        painter.setPen(Qt.PenStyle.NoPen)
        
        path = QPainterPath()
        # Hood/Head shape
        path.moveTo(32, 5)
        path.cubicTo(10, 15, 10, 40, 15, 55) # Left side
        path.lineTo(49, 55) # Bottom
        path.cubicTo(54, 40, 54, 15, 32, 5) # Right side
        
        # Face shadow (empty space)
        path.moveTo(32, 15)
        path.lineTo(25, 35)
        path.lineTo(39, 35)
        path.closeSubpath()
        
        painter.drawPath(path)
        
    elif kind == "book":
        # Ancient Tome
        # Cover
        painter.setBrush(QColor("#5D4037")) # Leather Brown
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(12, 8, 40, 48)
        painter.drawRoundedRect(rect, 2, 2)
        
        # Pages (side view)
        painter.setBrush(QColor("#D7CCC8")) # Aged Paper
        painter.drawRect(48, 10, 6, 44)
        
        # Spine details
        painter.setBrush(QColor("#3E2723")) # Darker Brown
        painter.drawRect(12, 8, 8, 48)
        
        # Gold Clasp/Symbol
        painter.setBrush(QColor("#FFC107")) # Gold
        painter.drawEllipse(25, 25, 10, 10)
        
    elif kind == "skull":
        # Monster Skull
        painter.setBrush(QColor("#E74C3c")) # Red
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Cranium
        painter.drawEllipse(17, 10, 30, 30)
        # Jaw
        painter.drawRect(22, 35, 20, 15)
        
        # Eyes
        painter.setBrush(QColor("#1b1f27"))
        painter.drawEllipse(22, 20, 8, 8)
        painter.drawEllipse(34, 20, 8, 8)
        
    elif kind == "shield":
        # Equipment Shield
        painter.setBrush(QColor("#3498DB")) # Blue
        painter.setPen(Qt.PenStyle.NoPen)
        
        path = QPainterPath()
        path.moveTo(15, 10)
        path.lineTo(49, 10)
        path.lineTo(49, 30)
        path.cubicTo(49, 50, 32, 60, 32, 60)
        path.cubicTo(32, 60, 15, 50, 15, 30)
        path.closeSubpath()
        painter.drawPath(path)
        
        # Cross on shield
        painter.setPen(QPen(QColor("#ECF0F1"), 3))
        painter.drawLine(32, 15, 32, 50)
        painter.drawLine(20, 25, 44, 25)

    elif kind == "scroll":
        # Spell Scroll
        painter.setBrush(QColor("#9B59B6")) # Purple
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Scroll Body
        painter.drawRect(18, 12, 28, 40)
        
        # Rolled ends
        painter.setBrush(QColor("#8E44AD")) # Darker Purple
        painter.drawEllipse(14, 10, 36, 6) # Top
        painter.drawEllipse(14, 48, 36, 6) # Bottom
        
        # Rune
        painter.setPen(QPen(QColor("#ECF0F1"), 2))
        painter.drawLine(25, 25, 39, 35)
        painter.drawLine(39, 25, 25, 35)

    painter.end()
    return QIcon(pixmap)


class _TileButton(QToolButton):
    """Stylised tool button that looks like a dashboard tile."""

    def __init__(self, title: str, subtitle: str, icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("class", "TileButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 140)
        self.setCheckable(False)
        
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIcon(icon)
        self.setIconSize(QSize(64, 64))
        
        sub_line = f"\n{subtitle}" if subtitle else ""
        self.setText(f"{title}{sub_line}")


class LauncherWindow(FramelessWindow):
    """Home screen that routes users to specific Living Scroll subprograms."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Living Scroll")
        self.setWindowIcon(get_app_icon())
        self.resize(900, 400)

        self._app_context = ApplicationContext()
        self._child_windows: List[QWidget] = []

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title_label = QLabel("Choose a workspace")
        title_label.setStyleSheet("font-size: 24px; font-weight: 600;")
        header_row = QHBoxLayout()
        header_row.addWidget(title_label)
        header_row.addStretch()
        settings_button = QPushButton("Global Settings…")
        settings_button.clicked.connect(self._open_global_settings)
        header_row.addWidget(settings_button)
        layout.addLayout(header_row)

        # Tiles row
        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(20)
        layout.addLayout(tiles_layout)

        tiles = [
            ("Characters", "", "silhouette", self._open_character_sheet_workspace),
            ("Spell Grapher", "", "graph", self._open_spell_grapher),
            ("Ruleset", "", "book", self._open_compendium),
            ("Bestiary", "", "skull", self._open_monster_manual),
            ("Equipment", "", "shield", self._open_equipment_manager),
            ("Grimoire", "", "scroll", self._open_spell_browser),
        ]

        for title, subtitle_text, icon_kind, handler in tiles:
            icon = _create_tile_icon(icon_kind)
            button = _TileButton(title, subtitle_text, icon)
            button.clicked.connect(handler)
            tiles_layout.addWidget(button)

        layout.addStretch()
        self.setCentralWidget(central)
        
        self._setup_tray()

    def _setup_tray(self) -> None:
        """Initialize the system tray icon and menu."""
        from modules.core.services.settings import get_settings
        settings = get_settings()
        
        # If disabled, do not show tray, standard behavior
        if not settings.minimize_to_tray:
            return

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        app = QApplication.instance()
        # Important: Allow app to run when launcher is hidden
        app.setQuitOnLastWindowClosed(False)

        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self.windowIcon())
        self._tray_icon.setToolTip("Living Scroll")

        menu = QMenu()
        
        # Main Actions
        show_action = QAction("Show Launcher", self)
        show_action.triggered.connect(self.showNormal) # Ensure normal state
        show_action.triggered.connect(self.activateWindow)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Modules
        module_actions = [
            ("Characters", self._open_character_sheet_workspace),
            ("Spell Grapher", self._open_spell_grapher),
            ("Ruleset", self._open_compendium),
            ("Bestiary", self._open_monster_manual),
            ("Equipment", self._open_equipment_manager),
            ("Grimoire", self._open_spell_browser),
        ]
        
        for name, handler in module_actions:
            action = QAction(name, self)
            action.triggered.connect(handler)
            menu.addAction(action)
            
        menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.show()
        
        # Double click to restore
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()
            
    def changeEvent(self, event):
        from PySide6.QtCore import QEvent, QTimer
        from modules.core.services.settings import get_settings
        
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and get_settings().minimize_to_tray:
                # Hide from taskbar. Use timer to ensure it applies after minimize animation/logic
                QTimer.singleShot(0, self.hide)
                
        super().changeEvent(event)

    def closeEvent(self, event):
        # User requested close -> Quit App
        QApplication.quit()

    # ------------------------------------------------------------------
    # Tile handlers
    # ------------------------------------------------------------------
    def _register_window(self, window: QWidget) -> None:
        self._child_windows.append(window)

        def _cleanup(_: object = None, *, ref=window) -> None:
            if ref in self._child_windows:
                self._child_windows.remove(ref)

        window.destroyed.connect(_cleanup)

    def _open_spell_grapher(self) -> None:
        logging.info("Opening Spell Grapher")
        from modules.spell_grapher.ui.window import MainWindow  # Lazy import
        window = MainWindow(app_context=self._app_context)
        self._register_window(window)
        window.show()

    def _open_character_sheet_workspace(self) -> None:
        logging.info("Opening Character Sheet Workspace")
        from modules.character_sheet.ui.hub import CharacterSheetHubWindow  # Lazy import
        window = CharacterSheetHubWindow(self._app_context, parent=self)
        self._register_window(window)
        window.show()

    def _open_compendium(self) -> None:
        logging.info("Opening Compendium")
        from modules.rules_explorer_explorer.ui.window import CompendiumWindow  # Lazy import
        window = CompendiumWindow(self)
        self._register_window(window)
        window.show()

    def _open_monster_manual(self) -> None:
        logging.info("Opening Monster Manual")
        from modules.bestiary.ui.window import MonsterWindow  # Lazy import
        window = MonsterWindow(self)
        self._register_window(window)
        window.show()

    def _open_equipment_manager(self) -> None:
        logging.info("Opening Equipment Manager")
        from modules.equipment.ui.window import EquipmentWindow  # Lazy import
        window = EquipmentWindow(self)
        self._register_window(window)
        window.show()

    def _open_spell_browser(self) -> None:
        logging.info("Opening Spell Browser")
        from modules.grimoire.ui.window import SpellWindow  # Lazy import
        window = SpellWindow(self)
        self._register_window(window)
        window.show()

    def _open_global_settings(self) -> None:
        logging.info("Opening Global Settings Dialog")
        dialog = GlobalSettingsDialog(self)
        dialog.show()

    def notify_character_updated(self) -> None:
        for window in list(self._child_windows):
            handler = getattr(window, "on_character_data_updated", None)
            if callable(handler):
                handler()


__all__ = ["LauncherWindow"]
