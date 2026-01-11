"""Application bootstrap helpers for Living Scroll."""

from __future__ import annotations

import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from modules.core.ui.resources import get_app_icon
from modules.core.ui.theme import DARK_THEME_STYLESHEET
from modules.dashboard.ui.window import LauncherWindow
from modules.core.services.logger import setup_logging
from modules.core.services.settings import get_settings

import logging
import traceback
from PySide6.QtWidgets import QMessageBox

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions by logging them and showing an error dialog."""
    # Log the full traceback
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    settings = get_settings()

    # Show a critical error message box if the application is running
    app = QApplication.instance()
    if app:
        if settings.dev_mode:
            from modules.core.ui.dialogs.dev_error_dialog import DevErrorDialog
            dialog = DevErrorDialog(exc_type, exc_value, exc_traceback)
            dialog.exec()
        else:
            logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            QMessageBox.critical(
                None,
                "Critical Error",
                f"An unexpected error occurred:\n\n{exc_value}\n\nSee logs for details."
            )

def main() -> int:
    """Launch the PySide6 GUI and return the application's exit code."""
    
    # Initialize logging first
    settings = get_settings()
    setup_logging("LivingScroll", debug=settings.dev_mode, enabled=settings.dev_mode)
    sys.excepthook = global_exception_handler
    
    logging.info("Starting Living Scroll application")

    # Suppress Qt warnings about monitor handles which are often false positives on Windows
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        # High DPI Scaling
        if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

        app = QApplication(sys.argv)
        app.setApplicationName("Living Scroll")
        app.setDesktopFileName("LivingScroll")
    
    app.setStyleSheet(DARK_THEME_STYLESHEET)

    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = LauncherWindow()
    window.show()
    
    logging.info("Launcher window shown")

    if owns_app:
        exit_code = app.exec()
        logging.info(f"Application exiting with code: {exit_code}")
        return exit_code

    return 0


__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
