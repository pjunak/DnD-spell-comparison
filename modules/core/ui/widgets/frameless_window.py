from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QMouseEvent, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizeGrip,
)

class CustomTitleBar(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(32)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(16, 16)
        self._icon_label.setScaledContents(True)
        layout.addWidget(self._icon_label)
        
        layout.addSpacing(8)

        self._title_label = QLabel()
        self._title_label.setObjectName("TitleBarLabel")
        layout.addWidget(self._title_label)
        
        layout.addStretch()
        
        self._center_layout = QHBoxLayout()
        self._center_layout.setContentsMargins(0, 0, 0, 0)
        self._center_layout.setSpacing(0)
        layout.addLayout(self._center_layout)
        
        layout.addStretch()

        self._btn_min = QPushButton("─")
        self._btn_min.setProperty("class", "TitleBarButton")
        self._btn_min.clicked.connect(self.window().showMinimized)
        layout.addWidget(self._btn_min)

        self._btn_max = QPushButton("☐")
        self._btn_max.setProperty("class", "TitleBarButton")
        self._btn_max.clicked.connect(self._toggle_maximize)
        layout.addWidget(self._btn_max)

        self._btn_close = QPushButton("✕")
        self._btn_close.setProperty("class", "TitleBarCloseButton")
        self._btn_close.clicked.connect(self.window().close)
        layout.addWidget(self._btn_close)

        self._start_pos: QPoint | None = None

    def _toggle_maximize(self) -> None:
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._start_pos:
            delta = event.globalPosition().toPoint() - self._start_pos
            win = self.window()
            win.move(win.pos() + delta)
            self._start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._start_pos = None
        
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()

    def update_info(self) -> None:
        win = self.window()
        self._title_label.setText(win.windowTitle())
        icon = win.windowIcon()
        if not icon.isNull():
            self._icon_label.setPixmap(icon.pixmap(16, 16))
        else:
            self._icon_label.clear()

    def set_center_widget(self, widget: QWidget) -> None:
        # Clear existing
        while self._center_layout.count():
            item = self._center_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._center_layout.addWidget(widget)

    def add_widget(self, widget: QWidget) -> None:
        # Insert before the minimize button (which is at count() - 3)
        # Layout: [Icon, Spacing, Title, Stretch, Min, Max, Close]
        # We want: [..., Stretch, Widget, Min, ...]
        layout = self.layout()
        if isinstance(layout, QHBoxLayout):
            # Find the index of the minimize button
            idx = layout.indexOf(self._btn_min)
            if idx >= 0:
                layout.insertWidget(idx, widget)
            else:
                layout.addWidget(widget)


class FramelessWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        
        # Container for custom layout
        self._frameless_container = QWidget()
        self._frameless_container.setObjectName("FramelessContainer")
        # Add a border to the container to define the window edge
        self._frameless_container.setStyleSheet("#FramelessContainer { border: 1px solid #3e3e42; background-color: #1e1e1e; }")
        
        super().setCentralWidget(self._frameless_container)
        
        self._frameless_layout = QVBoxLayout(self._frameless_container)
        self._frameless_layout.setContentsMargins(1, 1, 1, 1) # Show the border
        self._frameless_layout.setSpacing(0)
        
        # Title Bar
        self._title_bar = CustomTitleBar(self)
        self._frameless_layout.addWidget(self._title_bar)
        
        # Content Area
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._frameless_layout.addWidget(self._content_area)
        
        self._size_grip = QSizeGrip(self._frameless_container)
        self._size_grip.setStyleSheet("width: 16px; height: 16px; background-color: transparent;")
        
    def add_title_bar_widget(self, widget: QWidget) -> None:
        self._title_bar.add_widget(widget)

    def set_title_bar_center_widget(self, widget: QWidget) -> None:
        self._title_bar.set_center_widget(widget)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, '_size_grip'):
            rect = self.rect()
            self._size_grip.move(rect.right() - self._size_grip.width(), rect.bottom() - self._size_grip.height())
            self._size_grip.raise_()

    def setCentralWidget(self, widget: QWidget) -> None:
        # Clear existing content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._content_layout.addWidget(widget)
        
    def setWindowTitle(self, title: str) -> None:
        super().setWindowTitle(title)
        if hasattr(self, '_title_bar'):
            self._title_bar.update_info()

    def setWindowIcon(self, icon: QIcon) -> None:
        super().setWindowIcon(icon)
        if hasattr(self, '_title_bar'):
            self._title_bar.update_info()
