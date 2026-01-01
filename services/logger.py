"""Central logging configuration for SpellGraphix.

Provides setup_logging() to configure console and file logging with rotation.
"""

import sys
import logging
import platform
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_log_dir(app_name: str) -> Path:
    """Return the platform-specific directory for application logs."""
    system = platform.system()
    if system == "Windows":
        import os
        base = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")))
        return base / app_name / "Logs"
    elif system == "Darwin":
        return Path.home() / "Library" / "Logs" / app_name
    else:
        # Linux/Unix: XDG_STATE_HOME or ~/.local/state, fallback to ~/.cache if needed
        # We'll use XDG standard: ~/.local/state/app_name
        return Path.home() / ".local" / "state" / app_name / "logs"

def setup_logging(app_name: str = "SpellGraphix", debug: bool = False) -> None:
    """Configure root logger with console and rotating file handlers.
    
    Args:
        app_name: Name of the application (used for directory naming).
        debug: If True, set log level to DEBUG, else INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Ensure log directory exists
    log_dir = get_log_dir(app_name)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / (app_name.lower().replace(" ", "_") + ".log")
    
    # Create formatters and handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 1. Rotating File Handler (max 5MB, keep 3 backup files)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    
    # 2. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates if called multiple times
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info(f"Logging initialized. Writing logs to: {log_file}")
