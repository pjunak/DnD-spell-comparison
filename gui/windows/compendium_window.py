"""Compendium browser window.

This window is intentionally simple: pick a category, search, select an entry,
read the full rule text (if present).

It is backed by the filesystem compendium dataset loaded via services.compendium.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Tuple

from services.settings import get_settings
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.compendium import Compendium
from gui.utils.compendium_formatting import (
    slug,
    as_text,
    display_name,
    render_markdown_with_links,
    get_summary_md,
)

from ..resources import get_app_icon
from ..widgets import FramelessWindow


class CompendiumWindow(FramelessWindow):
    """Standalone compendium browser backed by the filesystem dataset."""

    _CATEGORIES: List[Tuple[str, str]] = [
        ("Rules", "rules"),
        ("Classes", "classes"),
        ("Feats", "feats"),
        ("Species", "species"),
        ("Backgrounds", "backgrounds"),
    ]

    

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compendium")
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1400, 800)

        self._compendium: Compendium | None = None
        self._entries: List[Tuple[str, Mapping[str, Any]]] = []
        self._dynamic_records: dict[str, Mapping[str, Any]] = {}

        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # --- Title Bar Controls ---
        title_controls = QWidget()
        title_layout = QHBoxLayout(title_controls)
        title_layout.setContentsMargins(0, 5, 0, 0)
        title_layout.setSpacing(10)
        
        self._category = QComboBox()
        for label, key in self._CATEGORIES:
            self._category.addItem(label, userData=key)
        self._category.currentIndexChanged.connect(self._reload_list)
        title_layout.addWidget(self._category)

        self._sort_label = QLabel("Sort:")
        self._sort_label.setVisible(False)
        title_layout.addWidget(self._sort_label)

        self._sort = QComboBox()
        self._sort.setVisible(False)
        self._sort.currentIndexChanged.connect(self._reload_list)
        title_layout.addWidget(self._sort)

        self._group_label = QLabel("Group:")
        self._group_label.setVisible(False)
        title_layout.addWidget(self._group_label)

        self._group = QComboBox()
        self._group.setVisible(False)
        self._group.currentIndexChanged.connect(self._reload_list)
        title_layout.addWidget(self._group)
        
        self.set_title_bar_center_widget(title_controls)

        # --- Main Splitter ---
        split = QSplitter(Qt.Orientation.Horizontal)
        self._splitter = split
        root.addWidget(split, 1)

        # --- Left Pane (Search + Filters + Nav) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search…")
        self._search.textChanged.connect(self._apply_search)
        left_layout.addWidget(self._search)


        self._nav_stack = QStackedWidget()
        # List navigation (most categories)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemSelectionChanged.connect(self._on_list_selection_changed)
        self._nav_stack.addWidget(self._list)

        # Rules navigation (tree mirroring folder structure)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self._nav_stack.addWidget(self._tree)


        left_layout.addWidget(self._nav_stack)
        split.addWidget(left_widget)

        # Right side container
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Dev mode button
        self._open_source_btn = QPushButton("Open Source File")
        self._open_source_btn.setVisible(False)
        self._open_source_btn.clicked.connect(self._on_open_source_clicked)
        self._open_source_btn.setStyleSheet("text-align: left; padding: 5px; background-color: #4a4a4a; color: #ffffff; border: none;")
        right_layout.addWidget(self._open_source_btn)

        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(False)
        self._details.anchorClicked.connect(self._on_anchor_clicked)
        self._details.setPlaceholderText("Select an entry to view its details.")
        right_layout.addWidget(self._details)

        split.addWidget(right_widget)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #5f6b7c;")
        root.addWidget(self._status)

        self.setCentralWidget(central)

        self._current_payload = None
        self._load_compendium()
        self._reload_list()

    # --- Loading -----------------------------------------------------
    def _load_compendium(self) -> None:
        try:
            self._compendium = Compendium.load()
            self._status.setText("Loaded compendium dataset.")
        except Exception as exc:  # noqa: BLE001
            self._compendium = None
            self._status.setText(f"Unable to load compendium dataset: {exc}")

    def _category_key(self) -> str:
        return str(self._category.currentData() or "")

    def _sort_key(self) -> str:
        return str(self._sort.currentData() or "")

    def _group_key(self) -> str:
        return str(self._group.currentData() or "")

    def _clear_spell_filters(self) -> None:
        self._level_buttons.blockSignals(True)
        self._school_buttons.blockSignals(True)
        for btn in self._level_buttons.buttons():
            btn.setChecked(False)
        for btn in self._school_buttons.buttons():
            btn.setChecked(False)
        self._level_buttons.blockSignals(False)
        self._school_buttons.blockSignals(False)
        self._apply_search()

    def _configure_group_controls(self, category_key: str) -> None:
        self._group.blockSignals(True)
        self._group.clear()
        self._group.blockSignals(False)
        self._group.setVisible(False)
        self._group_label.setVisible(False)

    def _configure_sort_controls(self, category_key: str) -> None:
        # Spells are grouped in a tree (level/school), so sort controls are hidden.
        if category_key != "spells":
            self._sort.blockSignals(True)
            self._sort.clear()
            self._sort.blockSignals(False)
            self._sort.setVisible(False)
            self._sort_label.setVisible(False)
            return

        self._sort.blockSignals(True)
        self._sort.clear()
        self._sort.blockSignals(False)
        self._sort.setVisible(False)
        self._sort_label.setVisible(False)

    @staticmethod
    def _spell_sort_tuple(payload: Mapping[str, Any], mode: str) -> tuple:
        name = str(payload.get("name") or payload.get("title") or "").strip().lower()
        school = str(payload.get("school") or "").strip().lower()
        level_raw = payload.get("level")
        try:
            level = int(level_raw) if level_raw is not None else 0
        except (TypeError, ValueError):
            level = 0

        if mode == "name":
            return (name, level, school)
        if mode == "school":
            return (school, name, level)
        # Default: level
        return (level, name, school)

    def _reload_list(self) -> None:
        self._entries = []
        self._list.blockSignals(True)
        self._list.clear()
        self._tree.blockSignals(True)
        self._tree.clear()
        self._clear_details()

        compendium = self._compendium
        if not compendium:
            self._status.setText("Compendium not loaded.")
            self._list.blockSignals(False)
            self._tree.blockSignals(False)
            return

        key = self._category_key()
        self._configure_sort_controls(key)
        self._configure_group_controls(key)
        if key == "rules":
            self._nav_stack.setCurrentWidget(self._tree)
            self._build_rules_tree(compendium)
        elif key == "classes":
            self._nav_stack.setCurrentWidget(self._tree)
            self._build_classes_tree(compendium)
        elif key == "species":
            self._nav_stack.setCurrentWidget(self._tree)
            self._build_species_tree(compendium)
        else:
            self._nav_stack.setCurrentWidget(self._list)
            records = compendium.records(key)
            for record in records:
                if not isinstance(record, Mapping):
                    continue
                label = display_name(record)
                self._entries.append((label, dict(record)))

            self._entries.sort(key=lambda pair: pair[0].lower())

        for label, payload in self._entries:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, payload)
            self._list.addItem(item)

        self._list.blockSignals(False)
        self._tree.blockSignals(False)
        
        self._splitter.setSizes([300, 700])
        self._apply_search()
        if key not in ("rules", "classes", "species"):
            self._status.setText(f"Showing {self._list.count()} entries.")

    # --- Wikidot-style tree removed --------------------------------

    def _build_classes_tree(self, compendium: Compendium) -> None:
        self._tree.clear()
        self._attach_classes_tree(compendium, self._tree.invisibleRootItem())
        # self._tree.expandToDepth(1)
        self._status.setText("Loaded classes tree.")

    def _attach_classes_tree(self, compendium: Compendium, parent: QTreeWidgetItem) -> None:
        classes = [c for c in compendium.records("classes") if isinstance(c, Mapping)]
        classes.sort(key=lambda c: display_name(c).lower())

        for klass in classes:
            klass_name = display_name(klass)
            klass_item = QTreeWidgetItem([klass_name])
            klass_item.setData(0, Qt.ItemDataRole.UserRole, dict(klass))
            parent.addChild(klass_item)

            subclasses = klass.get("subclasses")
            if isinstance(subclasses, list) and subclasses:
                sub_folder = QTreeWidgetItem(["Subclasses"])
                
                # Create a synthetic record for the Subclasses folder
                subs = [s for s in subclasses if isinstance(s, Mapping)]
                subs.sort(key=lambda s: display_name(s).lower())
                
                subclasses_page_md = ""
                for sub in subs:
                    sub_name = display_name(sub)
                    # Construct ID if missing, matching Compendium logic
                    sub_id = sub.get("id")
                    if not sub_id:
                        sub_id = f"subclass:{slug(klass_name)}:{slug(sub_name)}"
                    
                    subclasses_page_md += f"### [{sub_name}](compendium:{sub_id})\n\n"
                    
                    desc = as_text(sub)
                    subclasses_page_md += get_summary_md(desc)
                
                sub_folder.setData(0, Qt.ItemDataRole.UserRole, {
                    "name": f"{klass_name} Subclasses",
                    "page": {"full": subclasses_page_md}
                })
                
                klass_item.addChild(sub_folder)
                
                for sub in subs:
                    sub_item = QTreeWidgetItem([display_name(sub)])
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, dict(sub))
                    sub_folder.addChild(sub_item)

            # Warlock Invocations
            if klass_name == "Warlock":
                invocations = [i for i in compendium.records("invocations") if isinstance(i, Mapping)]
                if invocations:
                    inv_folder = QTreeWidgetItem(["Invocations"])
                    
                    # Synthetic page for Invocations
                    invocations.sort(key=lambda i: display_name(i).lower())
                    inv_page_md = ""
                    for inv in invocations:
                        inv_name = display_name(inv)
                        # Construct ID if missing
                        inv_id = inv.get("id")
                        if not inv_id:
                            inv_id = f"invocations:{slug(inv_name)}"
                        
                        inv_page_md += f"### [{inv_name}](compendium:{inv_id})\n\n"
                        
                        desc = as_text(inv)
                        inv_page_md += get_summary_md(desc)

                    inv_folder.setData(0, Qt.ItemDataRole.UserRole, {
                        "name": "Warlock Invocations",
                        "page": {"full": inv_page_md}
                    })
                    klass_item.addChild(inv_folder)
                    
                    # User requested to not list individual invocations in the tree, just the folder.
                    # for inv in invocations:
                    #     inv_item = QTreeWidgetItem([display_name(inv)])
                    #     inv_item.setData(0, Qt.ItemDataRole.UserRole, dict(inv))
                    #     inv_folder.addChild(inv_item)

            options = klass.get("options")
            if isinstance(options, list) and options:
                # Special handling for Warlock Pact Boons
                if klass_name == "Warlock":
                    # Identify the Pact Boon option block
                    # Collect all pact boon options to handle potential splits
                    pact_boon_options = [o for o in options if isinstance(o, Mapping) and o.get("key") == "warlock_pact_boon"]
                    other_options = [o for o in options if isinstance(o, Mapping) and o.get("key") != "warlock_pact_boon"]
                    
                    if pact_boon_options:
                        boon_folder = QTreeWidgetItem(["Pact Boons"])
                        
                        # Resolve the choices to actual records if possible
                        resolved_boons = []
                        seen_boon_names = set()
                        
                        # Try to find them in invocations first (since they are technically invocations in 2024)
                        all_invocations = {i.get("name"): i for i in compendium.records("invocations") if isinstance(i, Mapping)}
                        
                        for opt in pact_boon_options:
                            choices = opt.get("choices", [])
                            for choice in choices:
                                name = choice.get("label") or choice.get("value")
                                if not name or name in seen_boon_names:
                                    continue
                                
                                seen_boon_names.add(name)
                                
                                if name in all_invocations:
                                    resolved_boons.append(all_invocations[name])
                                else:
                                    # Fallback to the choice data itself
                                    # We use the description as the page content to avoid duplication in summary
                                    
                                    # Special handling for Pact of the Talisman which is missing full text
                                    desc = choice.get("description", "")
                                    if name == "Pact of the Talisman":
                                        desc = (
                                            "Source: Tasha's Cauldron of Everything / Player's Handbook\n\n"
                                            "Your patron gives you a special amulet, a talisman that can aid the wearer when the need is great. "
                                            "When the wearer fails an ability check, they can add a d4 to the roll, potentially turning the failure into a success. "
                                            "This benefit can be used a number of times equal to your proficiency bonus, and all expended uses are regained when you finish a long rest.\n\n"
                                            "If you lose the talisman, you can perform a 1-hour ceremony to receive a replacement from your patron. "
                                            "This ceremony can be performed during a short or long rest, and it destroys the previous amulet. "
                                            "The talisman turns to ash when you die."
                                        )
                                    else:
                                        desc = f"Source: Player's Handbook\n\n{desc}"

                                    fallback_record = {
                                        "name": name,
                                        "text": {"full": desc},
                                        "page": {"full": desc}
                                    }
                                    
                                    # Inherit source path from the option group or the class
                                    source_path = opt.get("_meta_source_path") or klass.get("_meta_source_path")
                                    if source_path:
                                        fallback_record["_meta_source_path"] = source_path

                                    resolved_boons.append(fallback_record)
                                    
                                    # Register dynamic record for linking
                                    boon_id = f"options:{slug(name)}"
                                    self._dynamic_records[boon_id] = fallback_record

                        # Synthetic page for Pact Boons
                        resolved_boons.sort(key=lambda o: display_name(o).lower())
                        boon_page_md = ""
                        for boon in resolved_boons:
                            boon_name = display_name(boon)
                            # Construct ID if missing
                            boon_id = boon.get("id")
                            if not boon_id:
                                # If it's an invocation, use invocation ID logic
                                if boon.get("category") == "eldritch_invocation":
                                    boon_id = f"invocations:{slug(boon_name)}"
                                else:
                                    # Fallback for generic options? 
                                    boon_id = f"options:{slug(boon_name)}"
                                    # Ensure it's registered if it wasn't already
                                    if boon_id not in self._dynamic_records and self._compendium.record_by_id(boon_id) is None:
                                         self._dynamic_records[boon_id] = boon
                            
                            boon_page_md += f"### [{boon_name}](compendium:{boon_id})\n\n"
                            
                            desc = as_text(boon)
                            boon_page_md += get_summary_md(desc)

                        boon_folder.setData(0, Qt.ItemDataRole.UserRole, {
                            "name": "Warlock Pact Boons",
                            "page": {"full": boon_page_md}
                        })
                        klass_item.addChild(boon_folder)
                        
                        for boon in resolved_boons:
                            boon_item = QTreeWidgetItem([display_name(boon)])
                            boon_item.setData(0, Qt.ItemDataRole.UserRole, dict(boon))
                            boon_folder.addChild(boon_item)
                    
                    # Process other options normally if any
                    if other_options:
                        opt_folder = QTreeWidgetItem(["Options"])
                        opt_folder.setData(0, Qt.ItemDataRole.UserRole, None)
                        klass_item.addChild(opt_folder)
                        other_options.sort(key=lambda o: display_name(o).lower())
                        for opt in other_options:
                            opt_item = QTreeWidgetItem([display_name(opt)])
                            opt_item.setData(0, Qt.ItemDataRole.UserRole, dict(opt))
                            opt_folder.addChild(opt_item)
                else:
                    # Standard behavior for other classes
                    opt_folder = QTreeWidgetItem(["Options"])
                    opt_folder.setData(0, Qt.ItemDataRole.UserRole, None)
                    klass_item.addChild(opt_folder)
                    opts = [o for o in options if isinstance(o, Mapping)]
                    opts.sort(key=lambda o: display_name(o).lower())
                    for opt in opts:
                        opt_item = QTreeWidgetItem([display_name(opt)])
                        opt_item.setData(0, Qt.ItemDataRole.UserRole, dict(opt))
                        opt_folder.addChild(opt_item)

    def _build_species_tree(self, compendium: Compendium) -> None:
        self._tree.clear()
        self._attach_species_tree(compendium, self._tree.invisibleRootItem())
        self._status.setText("Loaded species tree.")

    def _attach_species_tree(self, compendium: Compendium, parent: QTreeWidgetItem) -> None:
        species = [s for s in compendium.records("species") if isinstance(s, Mapping)]
        species.sort(key=lambda s: display_name(s).lower())

        for sp in species:
            sp_name = display_name(sp)
            sp_item = QTreeWidgetItem([sp_name])
            sp_item.setData(0, Qt.ItemDataRole.UserRole, dict(sp))
            parent.addChild(sp_item)

            subtypes = sp.get("subtypes")
            if not isinstance(subtypes, list) or not subtypes:
                continue
            
            subs = [t for t in subtypes if isinstance(t, Mapping)]
            subs.sort(key=lambda t: display_name(t).lower())
            for subtype in subs:
                name = display_name(subtype)
                record = {
                    "id": f"species:{slug(sp_name)}:{slug(name)}",
                    "name": name,
                    "data": dict(subtype),
                    "page": subtype.get("page") or {"full": self._format_species_subtype_page(sp, subtype)},
                }
                item = QTreeWidgetItem([name])
                item.setData(0, Qt.ItemDataRole.UserRole, record)
                sp_item.addChild(item)

    @staticmethod
    def _format_species_subtype_page(species_record: Mapping[str, Any], subtype_record: Mapping[str, Any]) -> str:
        species_name = str(species_record.get("name") or "").strip() or "(Species)"
        subtype_name = str(subtype_record.get("name") or "").strip() or "(Subtype)"
        lines: List[str] = [f"Summary\n- {species_name}: {subtype_name}\n"]
        abi = subtype_record.get("ability_bonus")
        if isinstance(abi, Mapping):
            ability = abi.get("ability")
            amount = abi.get("amount")
            if ability and amount is not None:
                lines.append("Ability Score Increase")
                lines.append(f"- {ability}: +{amount}")

        speed = subtype_record.get("speed")
        if speed is not None:
            lines.append("\nSpeed")
            lines.append(f"- {speed} ft")

        features = subtype_record.get("features")
        if isinstance(features, list) and features:
            lines.append("\nFeatures")
            for feat in features:
                if not isinstance(feat, Mapping):
                    continue
                name = str(feat.get("name") or "").strip()
                desc = str(feat.get("description") or "").strip()
                if name and desc:
                    lines.append(f"- {name}: {desc}")
                elif name:
                    lines.append(f"- {name}")

        return "\n".join(lines).strip() + "\n"


    def _apply_search(self) -> None:
        query = (self._search.text() or "").strip().lower()
        visible = 0

        # List filtering.
        if self._nav_stack.currentWidget() is self._list:
            for idx in range(self._list.count()):
                item = self._list.item(idx)
                label = (item.text() or "").lower()
                show = (not query) or (query in label)
                item.setHidden(not show)
                if show:
                    visible += 1
            self._status.setText(f"Showing {visible} entries.")
            return

        # Tree filtering (hide non-matching leaves; keep ancestor folders visible).
        def _filter_item(item: QTreeWidgetItem) -> bool:
            text = (item.text(0) or "").lower()
            any_child_visible = False
            for i in range(item.childCount()):
                child = item.child(i)
                if _filter_item(child):
                    any_child_visible = True
            is_leaf = item.childCount() == 0
            matches = (not query) or (query in text)
            show = any_child_visible or (is_leaf and matches) or (not is_leaf and matches)
            item.setHidden(not show)
            return show

        visible = 0
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            if top is not None and _filter_item(top):
                visible += 1
        self._status.setText("Filtered rules tree.")

    def _on_list_selection_changed(self) -> None:
        item = self._list.currentItem()
        if not item:
            self._clear_details()
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        self._render_payload(payload)

    def _on_tree_selection_changed(self) -> None:
        items = self._tree.selectedItems()
        item = items[0] if items else None
        if not item:
            self._clear_details()
            return
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if payload is None:
            return
        self._render_payload(payload)


    def _clear_details(self) -> None:
        self._details.setHtml("")
        self._open_source_btn.setVisible(False)
        self._current_payload = None

    def _render_payload(self, payload: object) -> None:
        self._current_payload = payload if isinstance(payload, Mapping) else None

        # Update dev button visibility
        settings = get_settings()
        has_source = False
        if isinstance(payload, Mapping):
            if "_meta_source_path" in payload:
                has_source = True
            elif "_rules_payload" in payload:
                rules = payload.get("_rules_payload")
                if isinstance(rules, Mapping) and "_meta_source_path" in rules:
                    has_source = True

        self._open_source_btn.setVisible(settings.dev_mode and has_source)

        compendium = self._compendium
        label_for_id = (lambda record_id: compendium.display_for_id(record_id)) if compendium else (lambda record_id: record_id)

        if isinstance(payload, Mapping):
            # Rules tree stores a wrapper that includes the raw rules payload.
            if "_rules_payload" in payload:
                rules_payload = payload.get("_rules_payload")
                record_id = payload.get("id")
                if isinstance(rules_payload, Mapping):
                    title = rules_payload.get("title")
                    header = str(title).strip() if isinstance(title, str) and title.strip() else str(record_id or "Rules")
                    references = rules_payload.get("references")
                    links_md = ""
                    if isinstance(references, list) and compendium:
                        refs = [str(v).strip() for v in references if str(v).strip()]
                        if refs:
                            parts = []
                            for ref in refs:
                                label = compendium.display_for_id(ref) or ref
                                parts.append(f'- [{label}](compendium:{ref})')
                            links_md = "### Links\n" + "\n".join(parts) + "\n\n"

                    text = as_text(rules_payload)
                    if text:
                        body = render_markdown_with_links(text, label_for_id=label_for_id)
                        # Ensure links_md is treated as HTML if we are using HTML mode
                        # links_md is currently Markdown "### Links\n[...](...)"
                        # We need to render links_md to HTML too if we join them.
                        links_html = render_markdown_with_links(links_md, label_for_id=label_for_id) if links_md else ""
                        
                        # Strip outer html tags from one of them or join bodies?
                        # render_markdown_with_links returns <html>...<body>...</body></html>
                        # We can't simple concat two <html> docs.
                        # We should likely just append the markdown references to the text BEFORE rendering.
                        
                        full_md = f"{links_md}{text}"
                        full_html = render_markdown_with_links(full_md, label_for_id=label_for_id)
                        self._details.setHtml(full_html)
                    else:
                        # Fallback for empty
                        self._details.setHtml(f"<html><body><h2>{header}</h2><p>{links_md}</p><p>No text available.</p></body></html>")
                else:
                    header = str(record_id or "Rules")
                    self._details.setHtml(f"<html><body><h2>{header}</h2><p>No text available.</p></body></html>")
                return

            header = display_name(payload)
            text = as_text(payload)
            references = payload.get("references")
            links_md = ""
            if isinstance(references, list) and compendium:
                refs = [str(v).strip() for v in references if str(v).strip()]
                if refs:
                    parts = []
                    for ref in refs:
                        label = compendium.display_for_id(ref) or ref
                        parts.append(f'- [{label}](compendium:{ref})')
                    links_md = "### Links\n" + "\n".join(parts) + "\n\n"

            if text:
                full_md = f"{links_md}{text}"
                full_html = render_markdown_with_links(full_md, label_for_id=label_for_id)
                self._details.setHtml(full_html)
            else:
                 # Construct valid HTML message
                 msg = (
                    f"<h2>{header}</h2>"
                    f"{render_markdown_with_links(links_md, label_for_id=label_for_id) if links_md else ''}"
                    "<p>No page text available for this entry yet.</p>"
                 )
                 self._details.setHtml(msg)
            return

        self._details.setHtml("<html><body><p>No details available.</p></body></html>")

    def _on_open_source_clicked(self) -> None:
        payload = self._current_payload
        if not payload:
            return

        source_path = payload.get("_meta_source_path")
        if not source_path and "_rules_payload" in payload:
            rules = payload.get("_rules_payload")
            if isinstance(rules, Mapping):
                source_path = rules.get("_meta_source_path")

        if not source_path:
            return

        path = Path(source_path)
        if not path.exists():
            self._status.setText(f"Source file not found: {path}")
            return

        # Open the file directly
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_anchor_clicked(self, url: QUrl) -> None:
        if not url.isValid():
            return
        if url.scheme() != "compendium":
            return
        record_id = url.path().lstrip("/")
        if not record_id:
            return
        self._open_by_id(record_id)

    def _open_by_id(self, record_id: str) -> None:
        compendium = self._compendium
        if not compendium:
            return
        payload = compendium.record_by_id(record_id)
        if payload is None:
            # Check dynamic records (e.g. synthetic options)
            payload = self._dynamic_records.get(record_id)
        
        if payload is None:
            self._status.setText(f"Unknown compendium id: {record_id}")
            return

        # Switch UI to the right category and select best-effort.
        if record_id.startswith("rules:"):
            for idx in range(self._category.count()):
                if str(self._category.itemData(idx) or "") == "rules":
                    self._category.setCurrentIndex(idx)
                    break
            self._select_rules_key(record_id[len("rules:") :])
            return

        # Non-rule: just render it directly.
        self._render_payload(payload)

    # --- Rules tree --------------------------------------------------
    def _build_rules_tree(self, compendium: Compendium) -> None:
        self._tree.clear()
        if not self._attach_rules_tree(compendium, None):
            self._status.setText("No rules blocks found in dataset.")
            return
        self._status.setText("Loaded rules tree.")

    def _attach_rules_tree(self, compendium: Compendium, parent_item: QTreeWidgetItem | None) -> bool:
        rules = compendium.payload.get("rules")
        if not isinstance(rules, Mapping):
            return False

        def _index_payload(folder_path: str) -> Mapping[str, Any] | None:
            key = f"{folder_path}/_index".strip("/") if folder_path else "_index"
            payload = rules.get(key)
            return payload if isinstance(payload, Mapping) else None

        def _title_from_path(path: str) -> str:
            last = (path.split("/")[-1] if path else "Rules").replace("_", " ").strip()
            return last.title() if last else "Rules"

        def _folder_title(folder_path: str) -> str:
            idx = _index_payload(folder_path)
            title = idx.get("title") if isinstance(idx, Mapping) else None
            if isinstance(title, str) and title.strip():
                return title.strip()
            return _title_from_path(folder_path)

        def _order_for(folder_path: str) -> List[str]:
            idx = _index_payload(folder_path)
            order = idx.get("order") if isinstance(idx, Mapping) else None
            if isinstance(order, list):
                return [str(v).strip() for v in order if str(v).strip()]
            return []

        # Collect leaf rule keys and folder paths.
        leaf_keys: List[str] = []
        folder_paths: set[str] = {""}
        for raw_key in rules.keys():
            if not isinstance(raw_key, str):
                continue
            if raw_key == "_index" or raw_key.endswith("/_index"):
                # Index/control files.
                continue
            key = raw_key.strip("/")
            if not key:
                continue
            leaf_keys.append(key)
            parts = [p for p in key.split("/") if p]
            for i in range(1, len(parts)):
                folder_paths.add("/".join(parts[:i]))

        # Build parent->children maps.
        child_folders: dict[str, List[str]] = {}
        for folder in sorted(folder_paths):
            if not folder:
                continue
            parent = folder.rsplit("/", 1)[0] if "/" in folder else ""
            child_folders.setdefault(parent, []).append(folder)

        child_leaves: dict[str, List[str]] = {}
        for leaf in leaf_keys:
            parent = leaf.rsplit("/", 1)[0] if "/" in leaf else ""
            child_leaves.setdefault(parent, []).append(leaf)

        # Precreate folder and leaf items.
        folder_items: dict[str, QTreeWidgetItem] = {}
        for folder in folder_paths:
            if folder == "":
                continue
            folder_items[folder] = QTreeWidgetItem([_folder_title(folder)])

        leaf_items: dict[str, QTreeWidgetItem] = {}
        for leaf in leaf_keys:
            payload = rules.get(leaf)
            title = None
            if isinstance(payload, Mapping):
                maybe_title = payload.get("title")
                if isinstance(maybe_title, str) and maybe_title.strip():
                    title = maybe_title.strip()
            display = title or _title_from_path(leaf)
            item = QTreeWidgetItem([display])
            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {
                    "id": f"rules:{leaf}",
                    "name": display,
                    "_rules_payload": payload,
                },
            )
            leaf_items[leaf] = item

        def _attach_children(folder_path: str, parent_item: QTreeWidgetItem | None) -> None:
            # Special case: if this is the root, and we have a root index with text, add "Start Here"
            if folder_path == "" and parent_item is None:
                root_idx = _index_payload("")
                if root_idx and (root_idx.get("text") or root_idx.get("page")):
                    hub_item = QTreeWidgetItem(["Start Here"])
                    hub_item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        {
                            "id": "rules:_index",
                            "name": root_idx.get("title", "Rules Hub"),
                            "_rules_payload": root_idx,
                        },
                    )
                    self._tree.addTopLevelItem(hub_item)
                    # Select it by default if it's the first thing we're adding
                    self._tree.setCurrentItem(hub_item)

            order = _order_for(folder_path)

            folders_here = child_folders.get(folder_path, [])
            leaves_here = child_leaves.get(folder_path, [])

            folders_by_name = {f.split("/")[-1]: f for f in folders_here}
            leaves_by_name = {l.split("/")[-1]: l for l in leaves_here}

            added_folders: set[str] = set()
            added_leaves: set[str] = set()

            def _add_item(item: QTreeWidgetItem) -> None:
                if parent_item is None:
                    if parent_item is None and parent_item_arg is None:
                        self._tree.addTopLevelItem(item)
                    elif parent_item_arg is not None:
                        parent_item_arg.addChild(item)
                else:
                    parent_item.addChild(item)

            # Add ordered items first.
            for name in order:
                if name in folders_by_name:
                    fp = folders_by_name[name]
                    if fp not in added_folders:
                        _add_item(folder_items[fp])
                        added_folders.add(fp)
                elif name in leaves_by_name:
                    lk = leaves_by_name[name]
                    if lk not in added_leaves:
                        _add_item(leaf_items[lk])
                        added_leaves.add(lk)

            # Add remaining folders/leaves alphabetically.
            for fp in sorted((f for f in folders_here if f not in added_folders), key=lambda v: folder_items[v].text(0).lower()):
                _add_item(folder_items[fp])
            for lk in sorted((l for l in leaves_here if l not in added_leaves), key=lambda v: leaf_items[v].text(0).lower()):
                _add_item(leaf_items[lk])

            # Recurse into folders.
            for fp in folders_here:
                _attach_children(fp, folder_items[fp])

        parent_item_arg = parent_item
        _attach_children("", None)
        return True


    def _select_rules_key(self, rule_key: str) -> None:
        # Best-effort: walk all items and match by stored id.
        needle = f"rules:{rule_key}"

        def _walk(item: QTreeWidgetItem) -> QTreeWidgetItem | None:
            payload = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(payload, Mapping) and payload.get("id") == needle:
                return item
            for i in range(item.childCount()):
                match = _walk(item.child(i))
                if match is not None:
                    return match
            return None

        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            if top is None:
                continue
            found = _walk(top)
            if found is not None:
                self._tree.setCurrentItem(found)
                return


__all__ = ["CompendiumWindow"]
