from __future__ import annotations

from typing import Any, List, Mapping

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import QHeaderView, QTableView, QWidget


class EquipmentTableModel(QAbstractTableModel):
    COLUMNS = [
        "Name",
        "Category",
        "Rarity",
        "Attunement",
        "Cost",
        "Weight",
    ]

    def __init__(self, items: List[Mapping[str, Any]], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items = items

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return item.get("name", "")
            elif col == 1:
                cats = item.get("categories", [])
                if not cats:
                    cats = item.get("tags", [])
                
                # Filter out redundant tags
                display_cats = [c for c in cats if c.lower() not in ["wondrous-item", "item"]]
                
                if display_cats:
                    return ", ".join(display_cats)
                return ""
            elif col == 2:
                rarity = item.get("rarity", "")
                return rarity
            elif col == 3:
                att = item.get("attunement")
                if att and (isinstance(att, list) and len(att) > 0) or att is True:
                    return "Yes"
                return "No"
            elif col == 4:
                cost = item.get("cost_gp", 0)
                # Fallback for string costs like "15 GP"
                if cost == 0:
                    c_str = str(item.get("cost", ""))
                    if "GP" in c_str:
                        try:
                            cost = float(c_str.replace("GP", "").strip())
                        except ValueError:
                            pass
                
                if cost >= 1:
                    return f"{cost:g} GP"
                elif cost >= 0.1:
                    return f"{cost*10:g} SP"
                elif cost > 0:
                    return f"{cost*100:g} CP"
                return str(item.get("cost", "—"))
            elif col == 5:
                w = item.get("weight_lb", 0)
                if w == 0:
                    w = item.get("weight", "—")
                return f"{w}"

        elif role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return item.get("name", "")
            elif col == 1:
                cats = item.get("categories", [])
                if not cats:
                    cats = item.get("tags", [])
                return ", ".join(cats) if cats else ""
            elif col == 2:
                rarity = item.get("rarity", "").lower()
                if "artifact" in rarity: return 6
                if "legendary" in rarity: return 5
                if "very rare" in rarity: return 4
                if "rare" in rarity: return 3
                if "uncommon" in rarity: return 2
                if "common" in rarity: return 1
                return 0
            elif col == 3:
                att = item.get("attunement")
                return 1 if (att and (isinstance(att, list) and len(att) > 0) or att is True) else 0
            elif col == 4:
                return item.get("cost_gp", 0.0)
            elif col == 5:
                return item.get("weight_lb", 0.0)

        if role == Qt.ItemDataRole.UserRole:
            return item

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section]
        return None
    
    def update_data(self, items: List[Mapping[str, Any]]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class EquipmentProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._filter_categories: set[str] = set()
        self._filter_text = ""
        self._filter_group = "All"
        self._filter_rarity: set[str] = set()
        self._filter_attunement: bool | None = None

    def set_category_filter(self, categories: set[str]) -> None:
        self._filter_categories = categories
        self.invalidateFilter()

    def set_text_filter(self, text: str) -> None:
        self._filter_text = text.lower()
        self.invalidateFilter()

    def set_group_filter(self, group_name: str) -> None:
        self._filter_group = group_name
        self.invalidateFilter()

    def set_rarity_filter(self, rarities: set[str]) -> None:
        self._filter_rarity = rarities
        self.invalidateFilter()

    def set_attunement_filter(self, attunement: bool | None) -> None:
        self._filter_attunement = attunement
        self.invalidateFilter()

    def _get_item_group(self, item: Mapping[str, Any]) -> str:
        item_type = str(item.get("type", "")).lower()
        tags = set(t.lower() for t in item.get("tags", []))
        categories = set(c.lower() for c in item.get("categories", []))
        all_tags = tags.union(categories)
        name = str(item.get("name", "")).lower()

        # Armor & Clothing
        # Catch "Armor (Plate)" etc, "Ring", "Shield", "Wondrous Item (tattoo)"
        if (
            "armor" in item_type or 
            "shield" in item_type or 
            "ring" in item_type or 
            any(t in all_tags for t in ["clothing", "boots", "head", "hands", "waist", "neck", "jewelry", "shield", "cloak", "outerwear", "armor", "ring"])
        ):
            return "Armor & Clothing"
        
        # Weapons
        # Catch "Weapon (Any)", "Staff", "Wand", "Rod"
        if (
            "weapon" in item_type or 
            "staff" in item_type or 
            "wand" in item_type or 
            "rod" in item_type or
            any(t in all_tags for t in ["weapon", "staff", "wand", "rod", "ammunition"])
        ):
            return "Weapons"
            
        # Consumables
        if (
            "potion" in item_type or 
            "scroll" in item_type or 
            "poison" in item_type or
            any(t in all_tags for t in ["potion", "scroll", "poison", "food", "drink", "consumable"])
        ):
            return "Consumables"
            
        # Vehicles & Mounts
        if (
            "vehicle" in item_type or 
            "mount" in item_type or 
            any(t in all_tags for t in ["mount", "vehicle"])
        ):
            return "Vehicles & Mounts"
            
        return "Miscellaneous"

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        item = model.data(index, Qt.ItemDataRole.UserRole)
        
        if not item:
            return False

        # Text filter
        if self._filter_text:
            name = item.get("name", "").lower()
            if self._filter_text not in name:
                return False

        # Group filter
        if self._filter_group and self._filter_group != "All":
            item_group = self._get_item_group(item)
            if item_group != self._filter_group:
                return False

        # Rarity filter
        if self._filter_rarity:
            rarity = item.get("rarity", "Common").lower()
            # Check if any selected rarity is in the item's rarity string
            if not any(r.lower() in rarity for r in self._filter_rarity):
                return False

        # Attunement filter
        if self._filter_attunement is not None:
            att = item.get("attunement")
            has_attunement = (att and (isinstance(att, list) and len(att) > 0) or att is True)
            if self._filter_attunement != has_attunement:
                return False

        # Category filter (Sub-filters within the group)
        if self._filter_categories:
            item_cats = set(item.get("categories", []))
            if not item_cats:
                item_cats = set(item.get("tags", []))
            
            normalized_cats = {c.lower() for c in item_cats}
            normalized_filters = {c.lower() for c in self._filter_categories}
            
            # Special handling for "Simple Weapon" and "Martial Weapon" which are categories but might not be tags
            item_category_field = item.get("category", "").lower()
            if "simple" in item_category_field: normalized_cats.add("simple weapon")
            if "martial" in item_category_field: normalized_cats.add("martial weapon")
            
            # Special handling for "Land Vehicle", "Water Vehicle", "Air Vehicle"
            # These might need to be inferred from tags or content if not explicit
            
            if not normalized_cats.intersection(normalized_filters):
                return False

        return True


class EquipmentTableView(QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setSortingEnabled(True)

        self._model = EquipmentTableModel([])
        self._proxy = EquipmentProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.ItemDataRole.EditRole)
        self.setModel(self._proxy)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

    def set_items(self, items: List[Mapping[str, Any]]) -> None:
        self._model.update_data(items)
        
        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        
        # Name stretches
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Others are interactive (fixed width but user adjustable)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

    def filter_categories(self, categories: set[str]) -> None:
        self._proxy.set_category_filter(categories)

    def filter_text(self, text: str) -> None:
        self._proxy.set_text_filter(text)

    def filter_group(self, group_name: str) -> None:
        self._proxy.set_group_filter(group_name)

    def filter_rarity(self, rarities: set[str]) -> None:
        self._proxy.set_rarity_filter(rarities)

    def filter_attunement(self, attunement: bool | None) -> None:
        self._proxy.set_attunement_filter(attunement)

    def get_selected_item(self) -> Mapping[str, Any] | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        
        # Map proxy index to source index
        proxy_index = indexes[0]
        source_index = self._proxy.mapToSource(proxy_index)
        
        return self._model.data(source_index, Qt.ItemDataRole.UserRole)
