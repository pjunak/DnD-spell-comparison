"""Window for displaying matplotlib figures with navigation controls."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

from ..resources import get_app_icon
from ..widgets import FramelessWindow


class GraphWindow(FramelessWindow):
    """Wrapper window that embeds a matplotlib figure with toolbar controls."""

    def __init__(self, figure, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        self.canvas = FigureCanvas(figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.canvas.draw()


__all__ = ["GraphWindow"]
