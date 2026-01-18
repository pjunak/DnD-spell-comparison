"""
Script to update feat YAML frontmatter with proper prerequisite, 
attribute_increase, proficiency, and expertise fields.
"""

import re
from pathlib import Path

FEAT_DIRS = [
    Path(r"c:\Users\junak\Documents\GitHub\Living-scroll\modules\compendium\data\dnd_2024\players_handbook\feats\general"),
    Path(r"c:\Users\junak\Documents\GitHub\Living-scroll\modules\compendium\data\dnd_2024\players_handbook\feats\origin"),
    Path(r"c:\Users\junak\Documents\GitHub\Living-scroll\modules\compendium\data\dnd_2024\players_handbook\feats\epic_boon"),
    Path(r"c:\Users\junak\Documents\GitHub\Living-scroll\modules\compendium\data\dnd_2024\players_handbook\feats\fighting_style"),
]

# Map feat names to their parsed data (manually curated based on content)
FEAT_DATA = {
    # General feats
    "Dual Wielder": {"prereq": "Level 4+, Strength or Dexterity 13+", "attr": ["STR", "DEX"], "cat": "general"},
    "Durable": {"prereq": "Level 4+", "attr": ["CON"], "cat": "general"},
    "Elemental Adept": {"prereq": "Level 4+, Spellcasting or Pact Magic Feature", "attr": ["INT", "WIS", "CHA"], "repeatable": True, "cat": "general"},
    "Fey Touched": {"prereq": "Level 4+", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "Grappler": {"prereq": "Level 4+, Strength or Dexterity 13+", "attr": ["STR", "DEX"], "cat": "general"},
    "Great Weapon Master": {"prereq": "Level 4+, Strength 13+", "attr": ["STR"], "cat": "general"},
    "Heavily Armored": {"prereq": "Level 4+, Medium Armor Training", "attr": ["STR", "CON"], "prof": {"armor": ["Heavy"]}, "cat": "general"},
    "Heavy Armor Master": {"prereq": "Level 4+, Heavy Armor Training", "attr": ["STR", "CON"], "cat": "general"},
    "Inspiring Leader": {"prereq": "Level 4+, Wisdom or Charisma 13+", "attr": ["WIS", "CHA"], "cat": "general"},
    "Keen Mind": {"prereq": "Level 4+", "attr": ["INT"], "cat": "general"},
    "Lightly Armored": {"prereq": "Level 4+", "attr": ["STR", "DEX"], "prof": {"armor": ["Light"]}, "cat": "general"},
    "Mage Slayer": {"prereq": "Level 4+", "attr": ["STR", "DEX"], "cat": "general"},
    "Martial Weapon Training": {"prereq": "Level 4+", "attr": ["STR", "DEX"], "prof": {"weapons": ["Martial"]}, "cat": "general"},
    "Medium Armor Master": {"prereq": "Level 4+, Medium Armor Training", "attr": ["STR", "DEX"], "cat": "general"},
    "Moderately Armored": {"prereq": "Level 4+, Light Armor Training", "attr": ["STR", "DEX"], "prof": {"armor": ["Medium", "Shields"]}, "cat": "general"},
    "Mounted Combatant": {"prereq": "Level 4+", "attr": ["STR", "DEX", "WIS"], "cat": "general"},
    "Observant": {"prereq": "Level 4+", "attr": ["INT", "WIS"], "cat": "general"},
    "Piercer": {"prereq": "Level 4+", "attr": ["STR", "DEX"], "cat": "general"},
    "Poisoner": {"prereq": "Level 4+", "attr": ["DEX", "INT"], "prof": {"tools": ["Poisoner's Kit"]}, "cat": "general"},
    "Polearm Master": {"prereq": "Level 4+, Strength or Dexterity 13+", "attr": ["STR", "DEX"], "cat": "general"},
    "Resilient": {"prereq": "Level 4+", "attr": ["any"], "cat": "general"},
    "Ritual Caster": {"prereq": "Level 4+, Intelligence, Wisdom, or Charisma 13+", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "Sentinel": {"prereq": "Level 4+, Strength or Dexterity 13+", "attr": ["STR", "DEX"], "cat": "general"},
    "Shadow Touched": {"prereq": "Level 4+", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "Sharpshooter": {"prereq": "Level 4+, Dexterity 13+", "attr": ["DEX"], "cat": "general"},
    "Shield Master": {"prereq": "Level 4+, Shield Training", "attr": ["STR", "DEX"], "cat": "general"},
    "Skill Expert": {"prereq": "Level 4+", "attr": ["any"], "prof": {"skills": ["any"]}, "expert": {"skills": ["any"]}, "cat": "general"},
    "Skulker": {"prereq": "Level 4+, Dexterity 13+", "attr": ["DEX"], "cat": "general"},
    "Slasher": {"prereq": "Level 4+", "attr": ["STR", "DEX"], "cat": "general"},
    "Speedy": {"prereq": "Level 4+, Dexterity or Constitution 13+", "attr": ["DEX", "CON"], "cat": "general"},
    "Spell Sniper": {"prereq": "Level 4+, Spellcasting or Pact Magic Feature", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "Telekinetic": {"prereq": "Level 4+", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "Telepathic": {"prereq": "Level 4+", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "War Caster": {"prereq": "Level 4+, Spellcasting or Pact Magic Feature", "attr": ["INT", "WIS", "CHA"], "cat": "general"},
    "Weapon Master": {"prereq": "Level 4+", "attr": ["STR", "DEX"], "prof": {"weapons": ["Martial"]}, "cat": "general"},
    
    # Origin feats (no level requirement)
    "Alert": {"prereq": None, "attr": None, "cat": "origin"},
    "Crafter": {"prereq": None, "attr": None, "prof": {"tools": ["Artisan's Tools (3)"]}, "cat": "origin"},
    "Healer": {"prereq": None, "attr": None, "cat": "origin"},
    "Lucky": {"prereq": None, "attr": None, "cat": "origin"},
    "Magic Initiate": {"prereq": None, "attr": None, "cat": "origin"},
    "Musician": {"prereq": None, "attr": None, "prof": {"tools": ["Musical Instrument (3)"]}, "cat": "origin"},
    "Savage Attacker": {"prereq": None, "attr": None, "cat": "origin"},
    "Skilled": {"prereq": None, "attr": None, "prof": {"skills": ["any (3)"]}, "cat": "origin"},
    "Tavern Brawler": {"prereq": None, "attr": None, "cat": "origin"},
    "Tough": {"prereq": None, "attr": None, "cat": "origin"},
    
    # Epic Boons (Level 19+)
    "Boon of Combat Prowess": {"prereq": "Level 19+", "attr": ["STR", "DEX"], "cat": "epic_boon"},
    "Boon of Dimensional Travel": {"prereq": "Level 19+", "attr": ["INT", "WIS", "CHA"], "cat": "epic_boon"},
    "Boon of Energy Resistance": {"prereq": "Level 19+", "attr": ["DEX", "CON"], "cat": "epic_boon"},
    "Boon of Fate": {"prereq": "Level 19+", "attr": ["INT", "WIS", "CHA"], "cat": "epic_boon"},
    "Boon of Fortitude": {"prereq": "Level 19+", "attr": ["CON"], "cat": "epic_boon"},
    "Boon of Irresistible Offense": {"prereq": "Level 19+", "attr": ["STR", "DEX"], "cat": "epic_boon"},
    "Boon of Recovery": {"prereq": "Level 19+", "attr": ["CON"], "cat": "epic_boon"},
    "Boon of Skill": {"prereq": "Level 19+", "attr": ["any"], "expert": {"skills": ["any"]}, "cat": "epic_boon"},
    "Boon of Speed": {"prereq": "Level 19+", "attr": ["DEX"], "cat": "epic_boon"},
    "Boon of Spell Recall": {"prereq": "Level 19+", "attr": ["INT", "WIS", "CHA"], "cat": "epic_boon"},
    "Boon of the Night Spirit": {"prereq": "Level 19+", "attr": ["DEX", "WIS", "CHA"], "cat": "epic_boon"},
    "Boon of Truesight": {"prereq": "Level 19+", "attr": ["CON"], "cat": "epic_boon"},
    
    # Fighting Styles (no ability increase, no proficiency)
    "Archery": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Blind Fighting": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Defense": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Dueling": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Great Weapon Fighting": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Interception": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Protection": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Thrown Weapon Fighting": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Two-Weapon Fighting": {"prereq": None, "attr": None, "cat": "fighting_style"},
    "Unarmed Fighting": {"prereq": None, "attr": None, "cat": "fighting_style"},
}

def parse_feat_file(path: Path) -> tuple:
    """Read feat file and return (yaml_end_line, content)"""
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # Find YAML frontmatter bounds
    yaml_start = -1
    yaml_end = -1
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if yaml_start < 0:
                yaml_start = i
            else:
                yaml_end = i
                break
    
    return yaml_end, lines

def update_feat_file(path: Path, data: dict):
    """Update feat file with new YAML frontmatter"""
    yaml_end, lines = parse_feat_file(path)
    if yaml_end < 0:
        print(f"  Skipping {path.name} - couldn't find YAML")
        return
    
    # Extract name and id from existing YAML
    name = None
    feat_id = None
    for line in lines[1:yaml_end]:
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("id:"):
            feat_id = line.split(":", 1)[1].strip()
    
    if not name:
        print(f"  Skipping {path.name} - no name found")
        return
    
    # Build new YAML
    cat = data.get("cat", "general")
    prereq = data.get("prereq")
    attr = data.get("attr")
    prof = data.get("prof")
    expert = data.get("expert")
    repeatable = data.get("repeatable", False)
    
    new_yaml = ["---"]
    new_yaml.append(f'name: {name}')
    new_yaml.append(f'type: feat')
    new_yaml.append(f'category: {cat}')
    
    if prereq:
        new_yaml.append(f'prerequisite: "{prereq}"')
    else:
        new_yaml.append(f'prerequisite: null')
    
    new_yaml.append(f'id: {feat_id}')
    
    if attr:
        new_yaml.append(f'attribute_increase: {attr}')
    else:
        new_yaml.append('attribute_increase: null')
    
    if prof:
        new_yaml.append('proficiency:')
        for k, v in prof.items():
            new_yaml.append(f'  {k}: {v}')
    else:
        new_yaml.append('proficiency: null')
    
    if expert:
        new_yaml.append('expertise:')
        for k, v in expert.items():
            new_yaml.append(f'  {k}: {v}')
    else:
        new_yaml.append('expertise: null')
    
    if repeatable:
        new_yaml.append('repeatable: true')
    
    new_yaml.append("---")
    
    # Combine with rest of file
    rest = lines[yaml_end + 1:]
    new_content = "\n".join(new_yaml + rest)
    
    path.write_text(new_content, encoding="utf-8")
    print(f"  Updated: {path.name}")

def main():
    updated = 0
    skipped = 0
    
    for feat_dir in FEAT_DIRS:
        if not feat_dir.exists():
            print(f"Directory not found: {feat_dir}")
            continue
        
        print(f"\nProcessing: {feat_dir.name}")
        
        for path in sorted(feat_dir.glob("*.md")):
            # Read to get feat name
            content = path.read_text(encoding="utf-8")
            name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
            if not name_match:
                print(f"  Skipping {path.name} - no name")
                skipped += 1
                continue
            
            name = name_match.group(1).strip().strip('"')
            
            if name in FEAT_DATA:
                update_feat_file(path, FEAT_DATA[name])
                updated += 1
            else:
                print(f"  No data for: {name}")
                skipped += 1
    
    print(f"\n\nDone! Updated: {updated}, Skipped: {skipped}")

if __name__ == "__main__":
    main()
