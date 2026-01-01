"""Application bootstrap helpers for SpellGraphix."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .resources import get_app_icon, DARK_THEME_STYLESHEET
from .windows import LauncherWindow
from services.logger import setup_logging

import logging
import traceback
from PySide6.QtWidgets import QMessageBox

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions by logging them and showing an error dialog."""
    # Log the full traceback
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    # Show a critical error message box if the application is running
    app = QApplication.instance()
    if app:
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(
            None,
            "Critical Error",
            f"An unexpected error occurred:\n\n{exc_value}\n\nSee logs for details."
        )

def main() -> int:
    """Launch the PySide6 GUI and return the application's exit code."""
    
    # Initialize logging first
    setup_logging("SpellGraphix", debug=False)
    sys.excepthook = global_exception_handler
    
    logging.info("Starting SpellGraphix application")

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("SpellGraphix")
        app.setDesktopFileName("SpellGraphix")
    
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
