"""Dialog for global application settings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from ..widgets import FramelessWindow
from modules.core.services.settings import get_settings, REQUIRED_MODULES
from modules.compendium.service import get_module_metrics


class GlobalSettingsDialog(FramelessWindow):
    """Global settings for rulesets, modules, and dev mode."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Global Settings")
        self.resize(500, 600)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._settings = get_settings()

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        heading = QLabel("Application Settings")
        heading.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(heading)

        # --- Ruleset Selection ---
        ruleset_group = QGroupBox("Ruleset Configuration")
        ruleset_layout = QVBoxLayout(ruleset_group)
        
        ruleset_layout.addWidget(QLabel("Select Ruleset:"))
        self._ruleset_combo = QComboBox()
        self._ruleset_combo.addItems(self._settings.available_rulesets())
        current_ruleset = self._settings.ruleset
        if current_ruleset in self._settings.available_rulesets():
            self._ruleset_combo.setCurrentText(current_ruleset)
        self._ruleset_combo.currentTextChanged.connect(self._on_ruleset_changed)
        ruleset_layout.addWidget(self._ruleset_combo)

        ruleset_layout.addWidget(QLabel("Active Modules:"))
        self._modules_list = QListWidget()
        ruleset_layout.addWidget(self._modules_list)
        
        layout.addWidget(ruleset_group)

        # --- Developer Options ---
        dev_group = QGroupBox("Developer Options")
        dev_layout = QVBoxLayout(dev_group)
        
        self._dev_mode_check = QCheckBox("Enable Developer Mode")
        self._dev_mode_check.setToolTip(
            "Enables application logging (console/file) and additional debug information.\n"
            "Also displays interactive error dialogs to jump to source code.\n"
            "Restart required for logging changes to take effect."
        )
        # Fix styling visibility issues: ensure indicator is visible and text contrasts well
        self._dev_mode_check.setChecked(self._settings.dev_mode)
        dev_layout.addWidget(self._dev_mode_check)
        
        self._tray_check = QCheckBox("Minimize to System Tray")
        self._tray_check.setToolTip("If enabled, minimizing the launcher will hide it to the system tray.\nClosing the launcher window will still quit the application.")
        self._tray_check.setChecked(self._settings.minimize_to_tray)
        dev_layout.addWidget(self._tray_check)
        
        layout.addWidget(dev_group)

        layout.addStretch()

        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initialize modules list
        self._populate_modules(current_ruleset)

    def _on_ruleset_changed(self, ruleset: str) -> None:
        self._populate_modules(ruleset)

    def _populate_modules(self, ruleset: str) -> None:
        self._modules_list.clear()
        available_ids = self._settings.available_modules(ruleset)
        active_ids = self._settings.active_modules
        
        # Gather metadata for sorting
        module_data = []
        for mod_id in available_ids:
            meta = self._settings.get_module_metadata(ruleset, mod_id)
            full_name = meta.get("full_name", mod_id)
            is_mandatory = meta.get("mandatory", False)
            # Fallback to hardcoded required list if metadata missing
            if mod_id in REQUIRED_MODULES:
                is_mandatory = True
                
            module_data.append({
                "id": mod_id,
                "name": full_name,
                "mandatory": is_mandatory
            })
            
        # Sort: Mandatory first, then Alphabetical by Name
        module_data.sort(key=lambda x: (not x["mandatory"], x["name"]))
        
        for data in module_data:
            mod_id = data["id"]
            name = data["name"]
            is_mandatory = data["mandatory"]
            
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, mod_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            is_active = (mod_id in active_ids) or is_mandatory
            
            if is_mandatory:
                item.setCheckState(Qt.CheckState.Checked)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setText(f"{name} (Required)")
            else:
                item.setCheckState(Qt.CheckState.Checked if is_active else Qt.CheckState.Unchecked)
            
            # Fetch and display metrics
            path = self._settings.get_module_path(ruleset, mod_id)
            if path:
                metrics = get_module_metrics(path)
                if metrics:
                    # Format as vertical list for tooltip
                    stats_lines = [f"{cnt} {k}" for k, cnt in metrics.items()]
                    item.setToolTip("\n".join(stats_lines))
                    # Removed inline text stats as requested to keep UI clean
                    # item.setText(f"{item.text()}  [{stats}]")

            self._modules_list.addItem(item)

    def _save_and_accept(self) -> None:
        # Save Ruleset
        self._settings.ruleset = self._ruleset_combo.currentText()
        
        # Save Modules
        active_modules = set()
        for i in range(self._modules_list.count()):
            item = self._modules_list.item(i)
            mod_id = item.data(Qt.ItemDataRole.UserRole)
            
            if item.checkState() == Qt.CheckState.Checked:
                active_modules.add(mod_id)
        
        self._settings.active_modules = active_modules
        
        # Save Dev Mode
        self._settings.dev_mode = self._dev_mode_check.isChecked()
        self._settings.minimize_to_tray = self._tray_check.isChecked()
        
        QMessageBox.information(self, "Settings Saved", "Settings saved. Please restart the application for changes to take full effect.")
        self.accept()

    def accept(self) -> None:
        self.close()

    def reject(self) -> None:
        self.close()


__all__ = ["GlobalSettingsDialog"]
