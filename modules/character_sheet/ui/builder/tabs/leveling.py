from __future__ import annotations

from __future__ import annotations

from typing import List, Dict, Any, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QHBoxLayout
)

from modules.character_sheet.model import CharacterSheet, ClassProgression
from modules.compendium.modifiers.state import ModifierStateSnapshot
from modules.compendium.service import Compendium
from modules.dnd24_mechanics.character_rules.models import FeatureOptionGroup, FeatureOptionChoice
from modules.character_sheet.ui.builder.widgets.level_entry import LevelEntry
from modules.character_sheet.ui.builder.dialogs.class_selection import ClassSelectionDialog

class LevelingTab(QWidget):
    def __init__(
        self,
        sheet: CharacterSheet,
        modifier_snapshot: ModifierStateSnapshot,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sheet = sheet
        self._modifier_snapshot = modifier_snapshot
        # Track local feature selections, initializing from sheet
        self._selections = dict(sheet.feature_options)
        self._compendium = Compendium.load()
        self._level_entries: List[LevelEntry] = []
        
        layout = QVBoxLayout(self)
        
        # Scrollable Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch() 
        self.scroll.setWidget(content)
        layout.addWidget(self.scroll)
        
        # Bottom Controls
        controls = QHBoxLayout()
        controls.addStretch()
        
        self.btn_add_level = QPushButton("Add Class Level...")
        self.btn_add_level.clicked.connect(self._on_add_level_clicked)
        self.btn_add_level.setStyleSheet("font-weight: bold; background-color: #4ec9b0; color: black;")
        controls.addWidget(self.btn_add_level)
        layout.addLayout(controls)
        
        self.refresh_from_sheet()

    def refresh_from_sheet(self):
        """Rebuild the timeline based on current sheet state."""
        # Store current scroll position to restore it after rebuild
        v_scroll_val = self.scroll.verticalScrollBar().value()
        
        # Sync proficiencies from feature_options to model first
        self._sync_proficiencies_from_selections()
        
        # Clear existing
        for entry in self._level_entries:
            entry.setParent(None)
            entry.deleteLater()
        self._level_entries.clear()
        
        # Remove widgets from layout (except stretch)
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Iterate classes
        # Note: This logic assumes classes are processed in order.
        for class_prog in self._sheet.identity.classes:
            class_name = class_prog.name
            target_level = class_prog.level
            
            # Fetch compendium data for descriptions
            class_record = self._compendium.class_record(class_name)
            
            # Iterate levels 1 to target_level
            for lvl in range(1, target_level + 1):
                # Features from Compendium (Visual descriptions)
                features_data = self._get_features_for_level(class_record, lvl, class_prog.subclass)
                
                # Options from Compendium - Build dynamically
                options_for_level = []
                
                # Skill Proficiency Options (Level 1 only for primary class)
                if lvl == 1 and class_record:
                    profs = class_record.get("proficiencies", {})
                    skills_choose = profs.get("skills_choose", 0)
                    skill_list = profs.get("skill_list", [])
                    
                    if skills_choose > 0 and skill_list:
                        # Get all available skills with enabled/disabled status
                        from modules.character_sheet.ui.builder.utils.selection_helpers import get_available_skill_proficiencies
                        available_all = get_available_skill_proficiencies(self._sheet, self._selections)
                        
                        # Filter to only show skills in the class list
                        # This preserves the 'enabled=False' status for skills already taken
                        choices = [opt for opt in available_all if opt.value in skill_list]

                        for i in range(skills_choose):
                            group_key = f"{class_name.lower()}_skill_{i+1}"
                            
                            # Use fixed width constant from helpers
                            from modules.character_sheet.ui.builder.utils.selection_helpers import SKILL_DROPDOWN_WIDTH
                            
                            group = FeatureOptionGroup(
                                key=group_key,
                                label=f"Skill Proficiency {i+1}",
                                description=f"Choose a skill proficiency from your class list.",
                                choices=choices,
                                required=True,
                                min_level=1,
                                width=SKILL_DROPDOWN_WIDTH
                            )
                            options_for_level.append(group)
                
                # Dynamic Subclass Selector - Check if any feature implies subclass choice
                # Common patterns: "Arcane Tradition", "Divine Domain", "Patron", "Monastic Tradition", etc.
                subclass_keywords = ["tradition", "domain", "patron", "college", "oath", "path", "circle", 
                                     "archetype", "origin", "discipline", "subclass", "school"]
                for feat in features_data:
                    feat_name_lower = feat.get("name", "").lower()
                    if any(kw in feat_name_lower for kw in subclass_keywords):
                        # This feature grants subclass choice
                        subclasses = class_record.get("subclasses", []) if class_record else []
                        if subclasses:
                            choices = [
                                FeatureOptionChoice(label=sub.get("name", "?"), value=sub.get("name", ""))
                                for sub in subclasses if isinstance(sub, dict)
                            ]
                            group_key = f"{class_name.lower()}_subclass"
                            group = FeatureOptionGroup(
                                key=group_key,
                                label=f"Choose {feat.get('name', 'Subclass')}",
                                description="Select your subclass specialization.",
                                choices=choices,
                                required=True,
                                min_level=lvl,
                                default=class_prog.subclass or ""
                            )
                            # Add if not already selected (or always show for editing)
                            options_for_level.append(group)
                            # If subclass is set, pre-populate in selections
                            if class_prog.subclass:
                                self._selections[group_key] = class_prog.subclass
                
                # Parse options from class progression YAML (expertise, fighting styles, etc.)
                if class_record:
                    progression = class_record.get("progression", [])
                    for prog_entry in progression:
                        if prog_entry.get("level") == lvl:
                            yaml_options = prog_entry.get("options", [])
                            for opt in yaml_options:
                                opt_key = opt.get("key", "")
                                opt_type = opt.get("type", "")
                                opt_label = opt.get("label", "Choose")
                                opt_choices = opt.get("choices", "")
                                
                                # Handle expertise type options
                                if opt_type == "expertise":
                                    from modules.character_sheet.ui.builder.utils.selection_helpers import get_available_skill_expertises
                                    available = get_available_skill_expertises(self._sheet, self._selections)
                                    if available:
                                        choices = available
                                        
                                        # Use fixed width constant from helpers
                                        from modules.character_sheet.ui.builder.utils.selection_helpers import SKILL_DROPDOWN_WIDTH
                                        
                                        group = FeatureOptionGroup(
                                            key=opt_key,
                                            label=opt_label,
                                            description="Choose a skill to gain expertise in.",
                                            choices=choices,
                                            required=False,
                                            min_level=lvl,
                                            width=SKILL_DROPDOWN_WIDTH
                                        )
                                        options_for_level.append(group)
                                
                entry = LevelEntry(
                    level=lvl,
                    class_name=class_name,
                    features=features_data,
                    parent=self
                )
                entry.set_options(options_for_level, self._selections)
                entry.choiceChanged.connect(self._on_choice_changed)
                entry.removeClicked.connect(self._on_remove_specific_level)
                
                # ASI/Feat Options - Detect from feature names instead of hardcoding
                # Look for "Ability Score Improvement" or similar in features_data
                asi_keywords = ["ability score improvement", "asi", "feat or ability"]
                has_asi_feature = any(
                    any(kw in feat.get("name", "").lower() for kw in asi_keywords)
                    for feat in features_data
                )
                
                if has_asi_feature:
                    from modules.character_sheet.ui.builder.widgets.asi_feat_widget import ASIFeatWidget
                    
                    group_key = f"{class_name.lower()}_asi_{lvl}"
                    current_selection = self._selections.get(group_key, "")
                    current_scores = {
                        name: self._sheet.get_ability(name).score 
                        for name in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
                    }
                    
                    # Calculate total character level for multiclass feat eligibility
                    # This is the sum of all class levels up to the current point
                    total_character_level = self._sheet.identity.level
                    
                    asi_widget = ASIFeatWidget(
                        group_key=group_key,
                        level=lvl,
                        current_selection=current_selection,
                        current_scores=current_scores,
                        character_level=total_character_level,
                        parent=entry
                    )
                    asi_widget.choiceChanged.connect(self._on_choice_changed)
                    # Connect feat selection to show inline options
                    asi_widget.featSelected.connect(
                        lambda feat_name, e=entry, gk=group_key: self._on_feat_selected(feat_name, e, gk)
                    )
                    entry.add_choice_widget(asi_widget)
                    
                    # Check if we already have a feat selected - show its options
                    if current_selection and not current_selection.startswith("ASI:"):
                        self._populate_feat_options(current_selection, entry, group_key)
                
                self.content_layout.insertWidget(self.content_layout.count() - 1, entry)
                self._level_entries.append(entry)
        
        # Restore scroll position
        # Use a timer to allow layout to settle
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(v_scroll_val))

    def _get_features_for_level(self, class_record: Dict[str, Any] | None, level: int, subclass_name: str | None = None) -> List[Dict[str, Any]]:
        """Get features from class progression and subclass (if applicable) for a given level."""
        if not class_record:
            return []
        features = []
        
        # 1. Class Progression Features
        progression = class_record.get("progression", [])
        if isinstance(progression, list):
            for entry in progression:
                if not isinstance(entry, dict):
                    continue
                if entry.get("level") == level:
                    for feat_name in entry.get("features", []):
                        features.append({"name": feat_name, "source": class_record.get("name", "Class")})
        
        # 2. Subclass Features (if subclass is selected)
        if subclass_name:
            subclasses = class_record.get("subclasses", [])
            for sub in subclasses:
                if not isinstance(sub, dict):
                    continue
                if sub.get("name", "").lower() == subclass_name.lower():
                    sub_progression = sub.get("progression", [])
                    if isinstance(sub_progression, list):
                        for entry in sub_progression:
                            if not isinstance(entry, dict):
                                continue
                            if entry.get("level") == level:
                                for feat_name in entry.get("features", []):
                                    features.append({"name": feat_name, "source": sub.get("name", "Subclass")})
                    break
        
        return features

    def _on_add_level_clicked(self):
        dialog = ClassSelectionDialog(self._sheet, parent=self)
        if dialog.exec():
            selected = dialog.get_selected_class()
            if not selected:
                return
                
            # Check if class exists
            active_class = next((c for c in self._sheet.identity.classes if c.name.lower() == selected.lower()), None)
            
            if active_class:
                active_class.level += 1
            else:
                self._sheet.identity.classes.append(ClassProgression(name=selected, level=1))
                
            self.refresh_from_sheet()

    def _on_remove_specific_level(self, level: int):
        """Remove a specific level from the character."""
        if not self._sheet.identity.classes:
            return
        
        # Find which class this level belongs to
        # We need to track which levels belong to which class
        # Build a flat list of (class_name, class_level_index) pairs
        level_map = []
        for cls in self._sheet.identity.classes:
            for lvl in range(1, cls.level + 1):
                level_map.append((cls.name, lvl))
        
        if level > len(level_map):
            return
        
        # Find the target class and reduce its level
        # We count levels in order they were added
        target_class_name, _ = level_map[level - 1]
        
        for cls in self._sheet.identity.classes:
            if cls.name == target_class_name:
                cls.level -= 1
                if cls.level <= 0:
                    self._sheet.identity.classes.remove(cls)
                break
        
        self.refresh_from_sheet()

    def _on_choice_changed(self, group_key: str, value: str):
        self._selections[group_key] = value
        self._sheet.feature_options[group_key] = value
        
        # Sync proficiencies to model based on selection type
        self._sync_proficiencies_from_selections()
        
        # Heuristic for Subclass update:
        # If the key contains "subclass" or the value looks like a subclass?
        # A robust way is needed, but for now we look for "subclass" in key.
        if "subclass" in group_key.lower() and value:
             # Find which class this belongs to.
             # We assume it belongs to the class that is currently being edited?
             # Or loop through classes and see if 'value' is a valid subclass for them?
             # Simple approach: Assign to first class for now (limitation).
             if self._sheet.identity.classes:
                 self._sheet.identity.classes[0].subclass = value
        
        self.refresh_from_sheet()
    
    def _sync_proficiencies_from_selections(self):
        """
        Rebuilds the entire proficiency model from scratch to ensure a single source of truth.
        Pipeline:
        1. Clear current proficiencies.
        2. Fetch & Apply Base Proficiencies (Background, Species, Class).
        3. Fetch & Apply User Selections (from feature_options).
        """
        # 1. Clear current state
        skill_profs = {}
        tool_profs = []
        
        # 2. Re-apply Base Proficiencies from Compendium
        
        # A. Background
        bg_name = self._sheet.identity.background
        if bg_name:
            # We need to find the background record. 
            # Assuming compendium structure or a helper.
            # Ideally this would be easier, but we scan for now.
            for bg in self._compendium.records("backgrounds"):
                if isinstance(bg, dict) and bg.get("name", "").lower() == bg_name.lower():
                    # Skills (e.g. Acolyte gives Insight, Religion)
                    for skill in bg.get("proficiencies", {}).get("skills", []):
                        if skill: skill_profs[skill] = 1
                    # Tools
                    for tool in bg.get("proficiencies", {}).get("tools", []):
                        if tool and tool not in tool_profs: tool_profs.append(tool)
                    break
        
        # B. Species (Ancestry)
        species_name = self._sheet.identity.ancestry
        if species_name:
            for sp in self._compendium.records("species"):
                if isinstance(sp, dict) and sp.get("name", "").lower() == species_name.lower():
                     for skill in sp.get("proficiencies", {}).get("skills", []):
                        if skill: skill_profs[skill] = 1
                     for tool in sp.get("proficiencies", {}).get("tools", []):
                        if tool and tool not in tool_profs: tool_profs.append(tool)
                     break

        # C. Class Base (e.g. Rogue Thieves' Tools)
        # We only care about base proficiencies here, not choices which are handled in step 3.
        for cls_prog in self._sheet.identity.classes:
            cls_record = self._compendium.class_record(cls_prog.name)
            if cls_record:
                # Fixed tools often listed in proficiencies
                # Note: Class skills are usually choices, so we skip them here.
                # However, some classes might have fixed skills (rare in 5e/2024 but possible).
                for tool in cls_record.get("proficiencies", {}).get("tools", []):
                     if tool and tool not in tool_profs: tool_profs.append(tool)

        # 3. Apply Feature Selections (User Choices)
        for key, value in self._sheet.feature_options.items():
            if not value:
                continue
            
            # Skill proficiencies (class skills like "rogue_skill_1" or feat skills)
            if "_skill_" in key and "_expertise" not in key:
                # Set proficiency level 1 if not already higher
                if value not in skill_profs or skill_profs[value] < 1:
                    skill_profs[value] = 1
            
            # Skill expertise (class expertise like "rogue_expertise_1_1" or feat expertise)
            elif "_expertise" in key:
                # Set expertise level 2
                skill_profs[value] = 2
            
            # Tool proficiencies
            elif "_tool_" in key:
                if value not in tool_profs:
                    tool_profs.append(value)
        
        # 4. Save to Model
        self._sheet.proficiencies.skills = skill_profs
        self._sheet.proficiencies.tools = tool_profs


    def _on_feat_selected(self, feat_name: str, entry: 'LevelEntry', group_key: str):
        """Handle feat selection - show inline options for the feat."""
        entry.clear_dynamic_options()
        self._populate_feat_options(feat_name, entry, group_key)
    
    def _populate_feat_options(self, feat_name: str, entry: 'LevelEntry', group_key: str):
        """Look up feat and add dynamic options if it has any."""
        # Find feat in compendium
        feat_record = None
        for feat in self._compendium.records("feats"):
            if isinstance(feat, dict) and feat.get("name", "").lower() == feat_name.lower():
                feat_record = feat
                break
        
        if not feat_record:
            return
        
        # Import helper functions
        from modules.character_sheet.ui.builder.utils.selection_helpers import (
            get_available_skill_proficiencies,
            get_available_skill_expertises,
            get_available_attributes,
            get_available_tool_proficiencies,
            ALL_SKILLS,
            SKILL_DROPDOWN_WIDTH
        )
        
        # Make key prefix from feat name
        feat_key_base = f"{feat_name.lower().replace(' ', '_')}"
        
        # Attribute increase options
        attr_increase = feat_record.get("attribute_increase")
        if attr_increase and isinstance(attr_increase, list):
            attr_key = f"{feat_key_base}_attribute"
            current_attr = self._selections.get(attr_key, "")
            
            # Get available attributes (not at 20+)
            available_attrs = get_available_attributes(
                self._sheet, 
                max_score=20, 
                pending_selections=self._selections,
                compendium=self._compendium
            )
            
            # Filter to only those allowed by the feat
            if "any" in [a.lower() for a in attr_increase]:
                options = available_attrs
            else:
                options = [a for a in attr_increase if a.upper() in available_attrs]
            
                if options:
                    # Use fixed width constant from helpers
                    
                    entry.add_dynamic_option(
                        label="Choose Attribute (+1)",
                        options=options,
                        current=current_attr,
                        key=attr_key,
                        width=SKILL_DROPDOWN_WIDTH
                    )
        
        # Skill proficiency options
        proficiency = feat_record.get("proficiency")
        if proficiency and isinstance(proficiency, dict):
            skills = proficiency.get("skills", [])
            if skills:
                skill_key = f"{feat_key_base}_skill_proficiency"
                current_skill = self._selections.get(skill_key, "")
                
                # Get available skills using helper
                available_skills = get_available_skill_proficiencies(
                    self._sheet, 
                    pending_selections=self._selections
                )
                
                # Filter if feat restricts options
                if skills == ["any"] or "any" in skills:
                    options = available_skills
                else:
                    options = [opt for opt in available_skills if opt.value in skills]
                
                if options:
                    entry.add_dynamic_option(
                        label="Choose Skill Proficiency",
                        options=options,
                        current=current_skill,
                        key=skill_key,
                        width=SKILL_DROPDOWN_WIDTH
                    )
        
        # Expertise options
        expertise = feat_record.get("expertise")
        if expertise and isinstance(expertise, dict):
            expert_skills = expertise.get("skills", [])
            if expert_skills:
                expertise_key = f"{feat_key_base}_skill_expertise"
                current_expertise = self._selections.get(expertise_key, "")
                
                # Get available expertise options using helper
                available_expertise = get_available_skill_expertises(
                    self._sheet, 
                    pending_selections=self._selections
                )
                
                # Filter if feat restricts options
                if expert_skills == ["any"] or "any" in expert_skills:
                    options = available_expertise
                else:
                    options = [opt for opt in available_expertise if opt.value in expert_skills]
                
                if options:
                    entry.add_dynamic_option(
                        label="Choose Skill Expertise",
                        options=options,
                        current=current_expertise,
                        key=expertise_key,
                        width=SKILL_DROPDOWN_WIDTH
                    )
        
        # Tool proficiency options
        if proficiency and isinstance(proficiency, dict):
            tools = proficiency.get("tools", [])
            if tools:
                tool_key = f"{feat_key_base}_tool_proficiency"
                current_tool = self._selections.get(tool_key, "")
                
                # Get available tools using helper
                available_tools = get_available_tool_proficiencies(
                    self._sheet, 
                    pending_selections=self._selections
                )
                
                # Filter if feat restricts options
                if tools == ["any"] or "any" in tools:
                    options = available_tools
                else:
                    # Tool helper returns strings or choices?
                    # I didn't verify tool helper update. Let's assume I missed updating tool helper to return choices?
                    # If tool helper still returns strings, then `[t in tools]` is correct.
                    # Let's double check tool helper.
                    pass
                    # If I didn't update tool helper, this code might break if I treat it as objects.
                    # Wait, looking at Step 3691, I updated `get_available_skill_proficiencies` and `get_available_skill_expertises`.
                    # I did NOT update `get_available_tool_proficiencies`.
                    # So tool helper returns strings.
                    # So original tool logic `[t for t in tools if t in available_tools]` is correct.
                    options = [t for t in tools if t in available_tools]
                
                if options:
                    entry.add_dynamic_option(
                        label="Choose Tool Proficiency",
                        options=options,
                        current=current_tool,
                        key=tool_key,
                        width=SKILL_DROPDOWN_WIDTH
                    )

