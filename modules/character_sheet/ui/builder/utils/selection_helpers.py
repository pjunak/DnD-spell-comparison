"""
Character Builder Selection Helpers

Reusable functions for filtering available options in character builder:
- Available skills for proficiency
- Available skills for expertise
- Available attributes for increase
"""

from __future__ import annotations

from typing import List, Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.character_sheet.model import CharacterSheet

# All standard D&D 5e/2024 skills
ALL_SKILLS = [
    "Acrobatics", "Animal Handling", "Arcana", "Athletics", 
    "Deception", "History", "Insight", "Intimidation",
    "Investigation", "Medicine", "Nature", "Perception",
    "Performance", "Persuasion", "Religion", "Sleight of Hand",
    "Stealth", "Survival"
]

# All attribute abbreviations
ALL_ATTRIBUTES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

# All standard tools
ALL_TOOLS = [
    "Alchemist's Supplies", "Brewer's Supplies", "Calligrapher's Supplies",
    "Carpenter's Tools", "Cartographer's Tools", "Cobbler's Tools",
    "Cook's Utensils", "Glassblower's Tools", "Jeweler's Tools",
    "Leatherworker's Tools", "Mason's Tools", "Painter's Supplies",
    "Potter's Tools", "Smith's Tools", "Tinker's Tools",
    "Weaver's Tools", "Woodcarver's Tools", "Thieves' Tools",
    "Navigator's Tools", "Forgery Kit", "Disguise Kit",
    "Herbalism Kit", "Poisoner's Kit"
]

# Calculate fixed width for skill dropdowns
# Max length of skill name * approx char width + padding
SKILL_DROPDOWN_WIDTH = (max(len(s) for s in ALL_SKILLS) * 9) + 50  # Increased slightly for safety

SKILL_ABILITY_MAP = {
    "Athletics": "STR",
    "Acrobatics": "DEX", "Sleight of Hand": "DEX", "Stealth": "DEX",
    "Arcana": "INT", "History": "INT", "Investigation": "INT", "Nature": "INT", "Religion": "INT",
    "Animal Handling": "WIS", "Insight": "WIS", "Medicine": "WIS", "Perception": "WIS", "Survival": "WIS",
    "Deception": "CHA", "Intimidation": "CHA", "Performance": "CHA", "Persuasion": "CHA"
}


from modules.dnd24_mechanics.character_rules import FeatureOptionChoice

def get_available_skill_proficiencies(
    sheet: 'CharacterSheet',
    pending_selections: Dict[str, str] | None = None
) -> List[FeatureOptionChoice]:
    """
    Get skills available for proficiency selection.
    Returns all skills, but marks already-proficient ones as disabled.
    """
    # Skills the character already has proficiency in (from unified model)
    existing_profs = set(sheet.proficiencies.skills.keys())
    
    # Also exclude skills selected in pending choices (current session, not yet synced)
    if pending_selections:
        for key, value in pending_selections.items():
            if ("_skill_" in key and "_expertise" not in key) and value:
                existing_profs.add(value)
    
    choices = []
    for skill in ALL_SKILLS:
        if skill in existing_profs:
            choices.append(FeatureOptionChoice(
                label=skill, 
                value=skill,
                enabled=False
            ))
        else:
            choices.append(FeatureOptionChoice(
                label=skill, 
                value=skill, 
                enabled=True
            ))
            
    return choices


def get_available_skill_expertises(
    sheet: 'CharacterSheet',
    pending_selections: Dict[str, str] | None = None
) -> List[FeatureOptionChoice]:
    """
    Get skills available for expertise selection.
    Must be proficient in the skill, but not already have expertise.
    """
    # Skills with proficiency (value >= 1)
    proficient_skills = set(
        skill for skill, level in sheet.proficiencies.skills.items() 
        if level >= 1
    )
    
    # Include pending proficiency choices
    if pending_selections:
        for key, value in pending_selections.items():
            if ("_skill_" in key and "_expertise" not in key) and value:
                proficient_skills.add(value)
    
    # Skills with existing expertise (value >= 2)
    existing_expertise = set(
        skill for skill, level in sheet.proficiencies.skills.items() 
        if level >= 2
    )
    
    # Include pending expertise selections
    if pending_selections:
        for key, value in pending_selections.items():
            if "_expertise" in key and value:
                existing_expertise.add(value)
    
    choices = []
    
    for skill in ALL_SKILLS:
        if skill in existing_expertise:
            choices.append(FeatureOptionChoice(
                label=skill, 
                value=skill,
                enabled=False
            ))
        elif skill not in proficient_skills:
            choices.append(FeatureOptionChoice(
                label=skill, 
                value=skill,
                enabled=False
            ))
        else:
             choices.append(FeatureOptionChoice(
                label=skill, 
                value=skill, 
                enabled=True
            ))
            
    return choices


def get_available_attributes(
    sheet: 'CharacterSheet',
    max_score: int = 20,
    pending_selections: Dict[str, str] | None = None,
    compendium = None
) -> List[str]:
    """
    Get attributes available for increase.
    
    Excludes attributes already at or above max_score (usually 20).
    
    Args:
        sheet: The character sheet
        max_score: Maximum allowed score (default 20)
        pending_selections: Dict of key -> value for pending choices
        compendium: Optional compendium for looking up feat bonuses
        
    Returns:
        List of attribute abbreviations that can be increased
    """
    available = []
    
    for attr in ALL_ATTRIBUTES:
        # Get current score including bonuses
        breakdown = sheet.get_ability_breakdown(attr, compendium)
        current_score = breakdown['total']
        
        # Count pending increases for this attribute
        pending_increase = 0
        if pending_selections:
            for key, value in pending_selections.items():
                if "_attribute" in key and value and value.upper() == attr:
                    pending_increase += 1
        
        # Allow if final score would be <= max_score
        if current_score + pending_increase < max_score:
            available.append(attr)
    
    return available


def get_available_tool_proficiencies(
    sheet: 'CharacterSheet',
    pending_selections: Dict[str, str] | None = None
) -> List[str]:
    """
    Get tools available for new proficiency selection.
    
    Args:
        sheet: The character sheet
        pending_selections: Dict of key -> value for pending choices
        
    Returns:
        List of tool names the character can gain proficiency in
    """
    # Tools the character already has proficiency in
    existing_tools = set(sheet.proficiencies.tools)
    
    # Also exclude tools selected in pending choices
    if pending_selections:
        for key, value in pending_selections.items():
            if "_tool_proficiency" in key and value:
                existing_tools.add(value)
    
    return [t for t in ALL_TOOLS if t not in existing_tools]
