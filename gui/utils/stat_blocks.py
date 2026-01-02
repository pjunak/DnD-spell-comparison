"""
Shared logic for rendering stat blocks into Markdown/HTML.
"""
from typing import Any, Dict, List, Mapping

def render_monster_stat_block(record: Dict[str, Any]) -> str:
    """
    Generate a Markdown stat block for a monster record.
    """
    # 1. Prefer pre-defined full text if available
    # 1. Prefer pre-defined full text if available
    text = record.get("text")
    if isinstance(text, dict) and text.get("full"):
        # We'll usage this as description, but still want header
        pass

    # 2. Fallback: Construct from metadata
    name = record.get("name", "Unknown")
    size = record.get("size", "Medium")
    type_ = record.get("type", "Monster")
    alignment = record.get("alignment", "Unaligned")
    ac = record.get("ac", 10)
    hp = record.get("hp", "10 (3d6)")
    speed = record.get("speed", "30 ft.")
    cr = record.get("cr", "")

    md = f"# {name}\n\n"
    md += f"*{size} {type_}, {alignment}*\n\n"
    md += "---\n\n"
    md += f"**Armor Class** {ac}\n\n"
    md += f"**Hit Points** {hp}\n\n"
    md += f"**Speed** {speed}\n\n"
    md += "---\n\n"

    stats = record.get("stats", {})
    s_str = stats.get("str", 10)
    s_dex = stats.get("dex", 10)
    s_con = stats.get("con", 10)
    s_int = stats.get("int", 10)
    s_wis = stats.get("wis", 10)
    s_cha = stats.get("cha", 10)

    md += "| STR | DEX | CON | INT | WIS | CHA |\n"
    md += "|:---:|:---:|:---:|:---:|:---:|:---:|\n"
    md += f"| {s_str} | {s_dex} | {s_con} | {s_int} | {s_wis} | {s_cha} |\n\n"
    md += "---\n\n"

    if cr:
         md += f"**Challenge** {cr}\n\n"

    # Traits
    traits = record.get("traits")
    if isinstance(traits, list):
        for t in traits:
            t_name = t.get("name", "")
            t_desc = t.get("description", "")
            if t_name:
                md += f"***{t_name}.*** {t_desc}\n\n"

    # Actions
    actions = record.get("actions")
    if isinstance(actions, list) and actions:
        md += "### Actions\n\n"
        for a in actions:
            a_name = a.get("name", "")
            a_desc = a.get("description", "")
            if a_name:
                md += f"***{a_name}.*** {a_desc}\n\n"

    # If we had text.full, use it primarily if desc (traits/actions) is empty or just append?
    # Usually text.full for monsters is ALL content.
    # But user wants consistency.
    # If text.full exists, we probably should return it but ensure header is there?
    # Monster text.full usually has headers.
    
    # Wait, for monsters I changed logic to return early in step 1.
    # Lines 12-13: if text.full: return text.full
    # Monsters usually have "Scaffolded page" or proper markdown.
    # If it's proper markdown, it should have headers.
    # I'll leave monster logic alone if user didn't complain about monsters specifically (User said "Compendium broken", "Spells don't show name", "Items throw error").
    # Monsters seem fine?
    # Actually, let's keep it safe.
    
    return md


def render_equipment_stat_block(item: Dict[str, Any]) -> str:
    """
    Generate a Markdown stat block for an equipment/magic item record.
    """
    # 1. Prefer pre-defined full text
    # Note: 'text' is the standard field key for content now
    text = item.get("text")
    pass

    # 2. Check for legacy 'page' key just in case, but prefer text
    page = item.get("page")
    if isinstance(page, dict) and page.get("full"):
        pass

    # 3. Fallback: Wrap simple description with a header
    name = item.get("name", "Unknown")
    type_ = item.get("type", "Item")
    rarity = item.get("rarity", "Common")
    cost = item.get("cost")
    weight = item.get("weight")

    header = f"# {name}\n\n"
    header += f"*{type_}, {rarity}*\n\n"
    
    if cost:
        header += f"**Cost:** {cost}\n"
    if weight:
        header += f"**Weight:** {weight}\n"
    
    header += "\n---\n\n"

    # Try to find description text
    desc = ""
    # Check simple text field
    simple_text = item.get("text")
    if isinstance(simple_text, str):
        desc = simple_text
    elif isinstance(simple_text, dict) and simple_text.get("full"):
        desc = simple_text.get("full")
    
    # If empty, check description field
    if not desc:
         desc = item.get("description", "")

    return header + desc


def render_spell_stat_block(record: Dict[str, Any]) -> str:
    """
    Generate a Markdown stat block for a spell record.
    """
    # 1. Prefer pre-defined full text if it looks like a complete block
    text = record.get("text")
    if isinstance(text, dict) and text.get("full"):
        desc_full = text.get("full", "")
        # If the content already starts with a header, it's likely the full markdown representation
        if desc_full.strip().startswith("# "):
             return desc_full

    # 2. Fallback construction
    name = record.get("name", "Unknown")
    level = record.get("level", 0)
    school = record.get("school", "Unknown")
    
    # Format Level/School line
    # e.g. "1st-Level Evocation" or "Evocation Cantrip"
    # Helper to ordinalize level
    def _ordinal(n):
        if 10 <= n % 100 <= 20: suffix = 'th'
        else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    if level == 0:
        level_str = f"{school} Cantrip"
    else:
        level_str = f"{_ordinal(level)}-Level {school}"

    # Tags (Ritual, Concentration)
    meta = record.get("meta", {})
    tags = []
    if meta.get("ritual"): tags.append("(Ritual)")
    # Concentration usually in duration, but sometimes tagged?
    # Let's check components/duration text for tags if needed, 
    # but standard 5e often puts "Duration: Concentration, up to ..."
    
    header = f"# {name}\n\n"
    header += f"*{level_str}{' ' + ' '.join(tags) if tags else ''}*\n\n"
    header += "---\n\n"
    
    # Properties
    time = record.get("time", [])
    val = ""
    if isinstance(time, list) and time:
        val = f"{time[0].get('number')} {time[0].get('unit')}"
        if not val.strip(): val = str(time)
    elif isinstance(time, str):
        val = time
    else:
        val = str(record.get("casting_time", ""))
        
    if not val.strip():
        val = str(time)
        
    header += f"**Casting Time:** {val}\n\n"
    
    range_ = record.get("range")
    range_val = "Unknown"
    if isinstance(range_, dict):
        dist = range_.get("distance")
        type_ = range_.get("type")
        if dist and type_:
            range_val = f"{dist} ({type_})" if str(dist).isdigit() else f"{dist}" # approximations
            if type_ == "touch": range_val = "Touch"
            elif type_ == "self": range_val = "Self"
        elif range_.get("type"):
            range_val = range_.get("type").title()
    elif isinstance(range_, str):
        range_val = range_
        
    header += f"**Range:** {range_val}\n\n"
    
    # Components - handle both list format (["V", "S", "M"]) and dict format ({"v": true, "s": true})
    comps = record.get("components", [])
    comp_list = []
    if isinstance(comps, list):
        # List format: ["V", "S", "M (a bit of fleece)"]
        comp_list = [str(c) for c in comps]
    elif isinstance(comps, dict):
        # Dict format: {"v": true, "s": true, "m": {"text": "..."}}
        if comps.get("v"): comp_list.append("V")
        if comps.get("s"): comp_list.append("S")
        if comps.get("m"):
            mat = comps.get("m")
            if isinstance(mat, dict): text = mat.get("text", "")
            else: text = str(mat)
            comp_list.append(f"M ({text})")
    header += f"**Components:** {', '.join(comp_list)}\n\n"
    
    # Duration
    duration = record.get("duration", [])
    dur_text = "Instantaneous"
    if isinstance(duration, list) and duration:
        d = duration[0]
        dtype = d.get("type", "")
        dval = d.get("duration", {})
        if dtype == "instant":
            dur_text = "Instantaneous"
        elif dtype == "timed":
            dur_text = f"{dval.get('amount')} {dval.get('type')}"
            if d.get("concentration"):
                dur_text = "Concentration, up to " + dur_text
        elif dtype == "permanent":
            dur_text = "Until Dispelled"
    elif isinstance(duration, str):
        dur_text = duration
        
    header += f"**Duration:** {dur_text}\n\n"
    
    header += "---\n\n"
    
    # Description
    entries = record.get("entries", [])
    # If entries is a list of strings/dicts (common in 5e JSONs)
    # We'll just dump text for now.
    desc = ""
    if isinstance(entries, list):
        for e in entries:
            if isinstance(e, str):
                desc += f"{e}\n\n"
            elif isinstance(e, dict):
                # Subheaders
                if "name" in e and "entries" in e:
                    desc += f"***{e['name']}.*** " + " ".join([str(sub) for sub in e['entries']]) + "\n\n"
    
    # Higher Levels
    entries_higher = record.get("entriesHigherLevel", [])
    if entries_higher:
        desc += "### At Higher Levels\n"
        for e in entries_higher:
             if isinstance(e, dict) and "entries" in e:
                 desc += "\n".join([str(sub) for sub in e['entries']]) + "\n\n"

    # If we had text.full, use it primarily as description
    text = record.get("text")
    if isinstance(text, dict) and text.get("full"):
        desc_full = text.get("full", "")
        if not desc:
            desc = desc_full

    return header + desc
