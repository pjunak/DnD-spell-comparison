from __future__ import annotations

from typing import Any, List, Mapping, Set
import re

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import QHeaderView, QTableView, QWidget


class SpellsTableModel(QAbstractTableModel):
    COLUMNS = [
        "Name",
        "Lvl",
        "School",
        "Casting Time",
        "Range",
        "Duration",
        "Comp",
        "R",
    ]

    def __init__(self, spells: List[Mapping[str, Any]], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._spells = spells

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._spells)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._spells)):
            return None

        spell = self._spells[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return spell.get("name", "")
            elif col == 1:
                return spell.get("level", 0)
            elif col == 2:
                return spell.get("school", "")
            elif col == 3:
                return self._format_casting_time(spell.get("casting_time", ""))
            elif col == 4:
                return spell.get("range", "")
            elif col == 5:
                return self._format_duration(spell.get("duration", ""), spell.get("concentration", False))
            elif col == 6:
                return self._format_components(spell.get("components", []), spell.get("materials", ""))
            elif col == 7:
                return "Yes" if spell.get("ritual") else "No"

        if role == Qt.ItemDataRole.UserRole:
            return spell

        return None

    def _format_casting_time(self, raw: str) -> str:
        raw = raw.strip()
        
        # Standardize Action/Bonus Action (remove "1 ")
        if raw.lower().startswith("1 action"):
            raw = raw[2:]
        elif raw.lower().startswith("1 bonus action"):
            raw = raw[2:]
            
        # Abbreviate units
        raw = raw.replace("minutes", "m").replace("minute", "m")
        raw = raw.replace("hours", "h").replace("hour", "h")
        
        # Check for standard types
        standard_types = ["Action", "Bonus Action", "Reaction"]
        for t in standard_types:
            if raw.lower() == t.lower():
                return t
            if raw.lower().startswith(t.lower()):
                # If it starts with standard type but has more text, append *
                # e.g. "Reaction which you take..." -> "Reaction *"
                return f"{t} *"
        
        # If it's something else (e.g. "1 minute"), keep it if short, else *
        if len(raw) > 15:
            return f"{raw[:12]}... *"
        return raw

    def _format_duration(self, raw: str, concentration: bool) -> str:
        raw = raw.strip()
        # Remove "Concentration, " prefix if present as we handle it separately
        if raw.lower().startswith("concentration, "):
            raw = raw[15:]
        elif raw.lower().startswith("concentration"):
            raw = raw[13:].strip(", ")

        # Abbreviate units
        raw = raw.replace("minutes", "m").replace("minute", "m")
        raw = raw.replace("hours", "h").replace("hour", "h")
        raw = raw.replace("rounds", "rnd").replace("round", "rnd")
        raw = raw.replace("days", "d").replace("day", "d")
        raw = raw.replace("Instantaneous", "Inst")
        
        if raw == "Until dispelled or triggered":
            raw = "Until triggered *"
        
        # Handle "up to" - user example kept it as "up to 10m"
        # But let's see if we can shorten it further if needed. 
        # User said "up to 10m" is fine.

        if concentration:
            return f"Con, {raw}"
        return raw

    def _format_components(self, components: List[str], materials: str) -> str:
        comps = ", ".join(components)
        # Check for gold cost or consumed materials in the materials string
        # Heuristic: look for "gp", "gold", "worth", "consume"
        if materials:
            mat_lower = materials.lower()
            # Simple heuristic for cost
            # Check if there is a number followed by gp/sp/cp or "worth"
            if re.search(r"\d+\s*(gp|gold|sp|cp)", mat_lower) or "worth" in mat_lower:
                comps += "*"
            # Previous logic was strict. User asked: "if component has monetary value given ... add *"
            # My previous implementation had similar check but let's make it robust with regex.
        return comps

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None
    
    def update_data(self, spells: List[Mapping[str, Any]]) -> None:
        self.beginResetModel()
        self._spells = spells
        self.endResetModel()


class SpellsProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._levels: Set[int] = set()
        self._schools: Set[str] = set()
        self._search_text: str = ""

    def set_filter_criteria(self, levels: Set[int], schools: Set[str], text: str) -> None:
        self._levels = levels
        self._schools = schools
        self._search_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        spell = model.data(index, Qt.ItemDataRole.UserRole)
        
        if not spell:
            return False

        # Level filter
        if self._levels:
            level = spell.get("level", 0)
            try:
                level = int(level)
            except (ValueError, TypeError):
                level = 0
            if level not in self._levels:
                return False

        # School filter
        if self._schools:
            school = str(spell.get("school", "")).strip().title()
            if school not in self._schools:
                return False

        # Text filter
        if self._search_text:
            # Search in name, school, level
            name = str(spell.get("name", "")).lower()
            school = str(spell.get("school", "")).lower()
            level = str(spell.get("level", 0))
            
            if (self._search_text not in name and 
                self._search_text not in school and 
                self._search_text not in level):
                return False

        return True


class SpellsTableView(QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(False)
        self.setSortingEnabled(True)

        self._proxy = SpellsProxyModel(self)
        super().setModel(self._proxy)

    def set_spells(self, spells: List[Mapping[str, Any]]) -> None:
        model = SpellsTableModel(spells, self)
        self._proxy.setSourceModel(model)
        
        # Optimize: Resize once based on content, then switch to Interactive
        # This prevents expensive recalculations on every paint/layout
        self.resizeColumnsToContents()
        
        header = self.horizontalHeader()
        # Name stretches
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Others are interactive (fixed width but user adjustable)
        for i in range(1, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

    def apply_filters(self, levels: Set[int], schools: Set[str], text: str) -> None:
        self._proxy.set_filter_criteria(levels, schools, text)

    def get_selected_spell(self) -> Mapping[str, Any] | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        proxy_index = indexes[0]
        source_index = self._proxy.mapToSource(proxy_index)
        return source_index.data(Qt.ItemDataRole.UserRole)
