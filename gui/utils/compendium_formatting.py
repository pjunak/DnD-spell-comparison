"""Utilities for formatting compendium content."""

from __future__ import annotations

import re
from typing import Any, List, Mapping


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def as_text(record: Mapping[str, Any]) -> str:
    # 1. Check for explicit page content.
    # We skip "scaffolded" pages if there is better source text available.
    page = record.get("page")
    page_text = ""
    if isinstance(page, str) and page.strip():
        page_text = page.strip()
    elif isinstance(page, Mapping):
        full = page.get("full")
        if isinstance(full, str) and full.strip():
            page_text = full.strip()
    
    if page_text and "(scaffolded page)" not in page_text:
        # Strip "Source: ..." lines to reduce clutter
        page_text = re.sub(r"^Source:.*$(\n)?", "", page_text, flags=re.MULTILINE)
        return page_text.strip()

    # 2. Check for 'text' (source content).
    text = record.get("text")
    if isinstance(text, str) and text.strip():
        return re.sub(r"^Source:.*$(\n)?", "", text.strip(), flags=re.MULTILINE).strip()
    if isinstance(text, Mapping):
        full = text.get("full")
        if isinstance(full, str) and full.strip():
            return re.sub(r"^Source:.*$(\n)?", "", full.strip(), flags=re.MULTILINE).strip()
        # Fall back to any string-like leaf.
        for candidate in ("description", "rules", "body"):
            leaf = text.get(candidate)
            if isinstance(leaf, str) and leaf.strip():
                return re.sub(r"^Source:.*$(\n)?", "", leaf.strip(), flags=re.MULTILINE).strip()

    # 3. Fallback to scaffolded page if we found nothing better.
    if page_text:
        return re.sub(r"^Source:.*$(\n)?", "", page_text, flags=re.MULTILINE).strip()

    # 4. Common patterns across compendium records.
    for key in ("short", "summary"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    description = record.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()

    # 5. Features list (e.g. Invocations, Class Features).
    features = record.get("features")
    parts = []
    
    # Add prerequisites if present (common in Invocations)
    prereqs = record.get("prerequisites")
    if isinstance(prereqs, list) and prereqs:
        prereq_texts = []
        for p in prereqs:
            if isinstance(p, Mapping):
                ptype = p.get("type")
                pvalue = p.get("value")
                plevel = p.get("level")
                if ptype == "level":
                    prereq_texts.append(f"Level {plevel}")
                elif ptype == "class":
                    if plevel:
                        prereq_texts.append(f"Level {plevel} {pvalue}")
                    else:
                        prereq_texts.append(f"{pvalue}")
                elif ptype == "spell":
                    prereq_texts.append(f"{pvalue} spell")
                elif ptype == "feature":
                    prereq_texts.append(f"{pvalue}")
                else:
                    prereq_texts.append(str(pvalue or ptype))
        if prereq_texts:
            parts.append(f"**Prerequisite:** {', '.join(prereq_texts)}")

    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, Mapping):
                name = feature.get("name")
                desc = feature.get("description")
                if name and desc:
                    parts.append(f"### {name}\n{desc}")
    
    if parts:
        return "\n\n".join(parts)

    return ""


def display_name(record: Mapping[str, Any]) -> str:
    name = record.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    title = record.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    key = record.get("key")
    if isinstance(key, str) and key.strip():
        return key.strip()
    record_id = record.get("id")
    if isinstance(record_id, str) and record_id.strip():
        return record_id.strip()
    return "(unnamed)"


def fix_wikidot_tables(text: str) -> str:
    """Convert Wikidot-style pipe tables to Markdown tables."""
    paragraphs = text.split('\n\n')
    new_paragraphs = []
    
    current_table = []
    
    def _render_table(rows: List[str]) -> str:
        if not rows:
            return ""
        
        # Parse rows to get column counts
        parsed_rows = []
        for r in rows:
            # r is like "| Cell 1 | Cell 2 |"
            parts = r.split('|')
            # Filter out empty start/end if they exist
            if len(parts) > 0 and parts[0].strip() == "": parts.pop(0)
            if len(parts) > 0 and parts[-1].strip() == "": parts.pop(-1)
            parsed_rows.append([c.strip() for c in parts])
            
        num_cols = [len(r) for r in parsed_rows]
        max_cols = max(num_cols) if num_cols else 0
        
        output = ""
        
        # Check for title row (1 col vs many)
        if len(parsed_rows) > 1 and num_cols[0] == 1 and max_cols > 1:
            title = parsed_rows[0][0]
            output += f"#### {title}\n\n"
            parsed_rows = parsed_rows[1:]
            num_cols = num_cols[1:]
            
        if not parsed_rows:
            return output

        # Reconstruct rows
        final_rows = []
        for r in parsed_rows:
            # Pad with empty cells if needed
            while len(r) < max_cols:
                r.append("")
            final_rows.append("| " + " | ".join(r) + " |")
            
        # Create separator
        separator = '|' + '|'.join(['---'] * max_cols) + '|'
        
        return output + f"{final_rows[0]}\n{separator}\n" + "\n".join(final_rows[1:]) + "\n"

    for p in paragraphs:
        if p.strip().startswith('|\n'):
            # Normalize row
            row = p.replace('|\n', '|')
            row = row.replace('\n', ' ')
            current_table.append(row)
        else:
            if current_table:
                new_paragraphs.append(_render_table(current_table))
                current_table = []
            new_paragraphs.append(p)
            
    if current_table:
        new_paragraphs.append(_render_table(current_table))
        
    return '\n\n'.join(new_paragraphs)



import os

_STYLESHEET = ""

def load_stylesheet():
    global _STYLESHEET
    if _STYLESHEET: return _STYLESHEET
    
    # Try to locate the css file
    # path is gui/resources/styles/markdown.css relative to project root
    # We are in gui/utils/compendium_formatting.py
    # So ../resources/styles/markdown.css
    base = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base, "resources", "styles", "markdown.css")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            _STYLESHEET = f.read()
    except Exception as e:
        print(f"Error loading stylesheet: {e}")
        _STYLESHEET = "body { font-family: serif; }"
        
    return _STYLESHEET

def simple_markdown_to_html(text: str) -> str:
    """
    Convert basic Markdown to HTML with embedded styles.
    Supported: Headers, Bold, Italic, Lists, HR.
    Tables are handled by fix_wikidot_tables (which outputs markdown tables, so we should convert those too or rely on text browser?)
    QTextBrowser has partial md support but setHtml overrides it.
    If we use setHtml we must provide full HTML.
    
    Let's use a chain of replacements.
    """
    html = text
    
    # Escape HTML to prevent injection (basic)
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Headers
    html = re.sub(r"^# (.*)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.*)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.*)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^#### (.*)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
    
    # HR
    html = re.sub(r"^---+$", r"<hr>", html, flags=re.MULTILINE)
    
    # Bold / Italic
    html = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
    
    # Lists (Simple) uses - or *
    # This is tricky with regex. Let's do a simple pass for lines starting with *
    html = re.sub(r"^\* (.*)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    # Wrap lis in ul? Only if consecutive.
    # For now, let's just make them bullets using unicode if we want lazy way, 
    # or leave as <li> which browser might accept without <ul> but distinct styling
    # is safer with full List replacement. 
    # Simplification: just replace * with bullet char for now to avoid complex parsing
    # html = re.sub(r"^\* (.*)$", r"&bull; \1<br>", html, flags=re.MULTILINE)
    
    # Line breaks
    html = html.replace("\n\n", "<br><br>")
    html = html.replace("\n", " ") # Collapse single newlines? Markdown rules are usually strict.
    # Actually, keep it simple: Double newline = paragraph. Single newline = space.
    # But for stats block we often strictly want headers to break. 
    # The header regexes handled their lines.
    
    # Tables
    # We have fix_wikidot_tables outputting Markdown tables: | col | col |
    # We need to convert them to HTML <table>
    # Minimal Table Parser
    lines = html.split("<br><br>")
    processed_blocks = []
    
    in_table = False
    table_html = []
    
    for block in lines:
        # Check if block looks like a table row (starts with |)
        # Note: we might have collapsed \n above so be careful.
        # Retrying without the \n collapse for table logic ease.
        pass

    return html

def convert_to_html_doc(md_text: str) -> str:
    # 1. Pre-process (Wikidot tables -> MD Tables)
    md_text = fix_wikidot_tables(md_text)
    
    # 2. Convert MD to HTML (Naive)
    # Use proper helper
    body = _naive_md_to_html(md_text)
    
    # 3. Wrap
    style = load_stylesheet()
    return f"<html><head><style>{style}</style></head><body>{body}</body></html>"


def _naive_md_to_html(text: str) -> str:
    """Robust-ish simple parser."""
    lines = text.split('\n')
    output = []
    
    in_list = False
    in_table = False
    
    for line in lines:
        sline = line.strip()
        
        # Headers
        if sline.startswith("# "):
            output.append(f"<h1>{sline[2:]}</h1>")
            continue
        elif sline.startswith("## "):
            output.append(f"<h2>{sline[3:]}</h2>")
            continue
        elif sline.startswith("### "):
            output.append(f"<h3>{sline[4:]}</h3>")
            continue
        elif sline.startswith("#### "):
            output.append(f"<h4>{sline[5:]}</h4>")
            continue
            
        # HR
        if sline.startswith("---") and len(sline.replace("-", "")) == 0:
            output.append("<hr>")
            continue

        # Tables
        if sline.startswith("|"):
            if not in_table:
                output.append("<table>")
                in_table = True
            
            # Row
            cols = [c.strip() for c in sline.strip("|").split("|")]
            # Header row check (---)
            if all(c.replace("-", "") == "" for c in cols):
                continue
            
            row_html = "<tr>"
            for c in cols:
                # Bold/Italic replacements in cell
                c = _inline_format(c)
                row_html += f"<td>{c}</td>"
            row_html += "</tr>"
            output.append(row_html)
            continue
        else:
            if in_table:
                output.append("</table>")
                in_table = False

        # Lists
        if sline.startswith("* ") or sline.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            item = sline[2:]
            item = _inline_format(item)
            output.append(f"<li>{item}</li>")
            continue
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
        
        # Paragraphs (Empty line handling)
        if not sline:
            output.append("<br>")
            continue
            
        # Standard text
        outline = _inline_format(sline)
        output.append(f"{outline}<br>")

    # Close open tags
    if in_list: output.append("</ul>")
    if in_table: output.append("</table>")
    
    return "\n".join(output)

def _inline_format(text: str) -> str:
    # Escape
    # html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") # Assume clean input for now to avoid breaking tags we might add? No, we should escape.
    # But logic above adds tags later.
    # Let's simple replacements
    
    # BoldItalic
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
    
    return text


_INLINE_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")



def render_markdown_with_links(text: str, *, label_for_id) -> str:
    """Process [[id]] links and render to full HTML doc."""
    # 1. Link replacement (on raw Markdown)
    
    # Strip "Source: ..." lines if they persist
    text = re.sub(r"(^|\n)(Source: [^\n]+)(\n|$)", r"\1\3", text)

    def _replace(match: re.Match[str]) -> str:
        raw = (match.group(1) or "").strip()
        if not raw:
            return match.group(0)
        display = str(label_for_id(raw) or raw).replace("]", "\\]")
        return f'[{display}](compendium:{raw})' # We keep MD link syntax for now? No, if we convert to HTML we should use <a href>
    
    # Actually, if we are converting to HTML, we should replace links with HTML anchors
    # But _naive_md_to_html doesn't handle MD links like [text](url).
    # It handles Bold/Italic. 
    # Let's handle link replacement AFTER md link resolution? 
    # Or change _replace to output HTML anchor.
    
    def _replace_html_anchor(match: re.Match[str]) -> str:
        raw = (match.group(1) or "").strip()
        if not raw: return match.group(0)
        display = str(label_for_id(raw) or raw)
        return f'<a href="compendium:{raw}">{display}</a>'

    # Replace [[id]] with HTML anchors directly
    text_with_links = _INLINE_LINK_RE.sub(_replace_html_anchor, text)
    
    # Also handle standard [text](url) links? 
    # Our _inline_format doesn't support them yet. 
    # Let's add basic support there or pre-process.
    text_with_links = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r'<a href="\2">\1</a>', text_with_links)
    
    return convert_to_html_doc(text_with_links)


def get_summary_md(text: str) -> str:
    if not text: return ""
    parts = text.split('\n\n')
    # Skip source lines
    body = next((p for p in parts if not p.strip().startswith("Source:")), None)
    md = ""
    if body: md += f"{body}\n\n"
    return md
