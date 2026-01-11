"""Custom error dialog for Developer Mode."""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QDialogButtonBox,
    QWidget,
)

class DevErrorDialog(QDialog):
    """Error dialog that allows opening the source file."""

    def __init__(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_traceback: Optional[object],
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Developer Error")
        self.resize(700, 500)
        
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.exc_traceback = exc_traceback
        
        # Extract last frame info
        self.file_path: Optional[Path] = None
        self.line_number: int = 0
        self._extract_location()

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Exception: {exc_type.__name__}")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #ff5555;")
        layout.addWidget(header)
        
        message = QLabel(str(exc_value))
        message.setWordWrap(True)
        message.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(message)

        # Traceback
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.text_area = QPlainTextEdit(tb_text)
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        layout.addWidget(self.text_area)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.open_btn = QPushButton("Open File")
        self.open_btn.clicked.connect(self._open_file)
        if not self.file_path or not self.file_path.exists():
            self.open_btn.setEnabled(False)
            self.open_btn.setText("File Not Found")
        else:
            self.open_btn.setText(f"Open {self.file_path.name}:{self.line_number}")
            
        button_layout.addWidget(self.open_btn)
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _extract_location(self) -> None:
        """Find the last interesting frame in the traceback."""
        try:
            # Iterate stack to find the last file that exists locally
            # We prefer files in our project over unrelated libraries if possible?
            # For now, just take the last frame.
            tb = self.exc_traceback
            while tb.tb_next:
                tb = tb.tb_next
            
            frame = tb.tb_frame
            self.file_path = Path(frame.f_code.co_filename)
            self.line_number = tb.tb_lineno
        except Exception:
            pass

    def _open_file(self) -> None:
        if not self.file_path:
            return
            
        try:
            # Try to open with VS Code first if available
            # Check if 'code' is in path
            # Or just use os.startfile on Windows
            if sys.platform == "win32":
                # Try to use VS Code CLI to jump to line
                # "code -g file:line"
                try:
                    subprocess.Popen(["code", "-g", f"{self.file_path}:{self.line_number}"], shell=True)
                except FileNotFoundError:
                    os.startfile(self.file_path)
            else:
                # Fallback for others (open generic)
                import webbrowser
                webbrowser.open(self.file_path.as_uri())
        except Exception as e:
            print(f"Failed to open file: {e}")
