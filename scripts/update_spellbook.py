#!/usr/bin/env python
"""Fetch the 2024 spell list and refresh spellbook.json."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import xml.etree.ElementTree as ET

import requests

BASE_URL = "http://dnd2024.wikidot.com"
INDEX_URL = f"{BASE_URL}/spell:all/noredirect/true/do=print"
DETAIL_SUFFIX = "/noredirect/true/do=print"
USER_AGENT = "DnDSpellSync/1.0 (+https://github.com/pjunak/DnD-spell-comparison)"
DEFAULT_SCALING_LEVELS = [1, 5, 11, 17]


@dataclass
class SpellListing:
    name: str
    slug: str
    level: int
    school: str
    classes: List[str]
    casting_time: str
    range: str
    components: str
    duration: str


@dataclass
class SpellDetail:
    source: Optional[str]
    metadata_fields: Dict[str, str]
    paragraphs: List[str]
    header_line: Optional[str]


UNMAPPED_METADATA_KEYS: Counter[str] = Counter()


class SpellListParser(HTMLParser):
    """Parse the spell index tables rendered on the Wikidot page."""

    def __init__(self) -> None:
        super().__init__()
        self.level_stack: List[Optional[int]] = []
        self.current_level: Optional[int] = None
        self.in_table = False
        self.current_row: List[Tuple[str, Optional[str]]] = []
        self.current_cell = ""
        self.current_link: Optional[str] = None
        self.current_tag: Optional[str] = None
        self.row_is_header = False
        self.current_headers: List[str] = []
        self.current_rows: List[List[Tuple[str, Optional[str]]]] = []
        self.tables: Dict[int, List[Dict[str, List]]] = {}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = dict(attrs)
        if tag == "div":
            div_id = attributes.get("id")
            if div_id and div_id.startswith("wiki-tab-0-"):
                level_idx = int(div_id.split("-")[-1])
                self.level_stack.append(level_idx)
                self.current_level = level_idx
            else:
                self.level_stack.append(None)
            return

        if tag == "table" and self.current_level is not None:
            class_attr = attributes.get("class") or ""
            if "wiki-content-table" in class_attr:
                self.in_table = True
                self.current_headers = []
                self.current_rows = []
            return

        if not self.in_table:
            return

        if tag == "tr":
            self.current_row = []
            self.row_is_header = True
            return

        if tag in ("td", "th"):
            self.current_cell = ""
            self.current_link = None
            if tag == "td":
                self.row_is_header = False
            self.current_tag = tag
            return

        if tag == "a" and self.current_tag in ("td", "th"):
            href = attributes.get("href")
            if href:
                self.current_link = href
            return

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.level_stack:
            finished = self.level_stack.pop()
            self.current_level = next((lvl for lvl in reversed(self.level_stack) if lvl is not None), None)
            return

        if tag == "table" and self.in_table:
            if self.current_level is not None:
                self.tables.setdefault(self.current_level, []).append(
                    {
                        "headers": list(self.current_headers),
                        "rows": list(self.current_rows),
                    }
                )
            self.in_table = False
            return

        if not self.in_table:
            return

        if tag in ("td", "th") and self.current_tag in ("td", "th"):
            text = unescape(self.current_cell.strip())
            self.current_row.append((text, self.current_link))
            self.current_cell = ""
            self.current_link = None
            self.current_tag = None
            return

        if tag == "tr" and self.current_row:
            if self.row_is_header:
                self.current_headers = [cell for cell, _ in self.current_row]
            else:
                self.current_rows.append(list(self.current_row))
            self.current_row = []
            return

    def handle_data(self, data: str) -> None:
        if self.in_table and self.current_tag in ("td", "th"):
            self.current_cell += data


def normalise_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_page_fragment(html: str) -> str:
    marker = '<div id="page-content">'
    start = html.find(marker)
    if start == -1:
        raise ValueError("page-content div not found")
    pos = start + len(marker)
    depth = 1
    idx = pos
    closing = "</div>"
    while depth > 0:
        next_open = html.find("<div", idx)
        next_close = html.find(closing, idx)
        if next_close == -1:
            raise ValueError("Unbalanced div structure in page content")
        if next_open != -1 and next_open < next_close:
            depth += 1
            idx = next_open + 4
        else:
            depth -= 1
            idx = next_close + len(closing)
    fragment = html[pos : idx - len(closing)]
    return f"<root>{fragment}</root>"


def element_text(node: ET.Element) -> str:
    parts: List[str] = []
    if node.text:
        parts.append(node.text)
    for child in node:
        parts.append(element_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def parse_metadata_paragraph(node: ET.Element) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for strong in node.findall("strong"):
        label = (strong.text or "").strip().rstrip(":")
        value = (strong.tail or "").strip()
        if label:
            key = label.lower().replace(" ", "_")
            fields[key] = normalise_whitespace(value)
    return fields


def parse_spell_detail(html: str) -> SpellDetail:
    fragment = extract_page_fragment(html)
    fragment = fragment.replace("&nbsp;", " ")
    root = ET.fromstring(fragment)

    source: Optional[str] = None
    header_line: Optional[str] = None
    metadata_fields: Dict[str, str] = {}
    paragraphs: List[str] = []
    metadata_consumed = False

    for child in root:
        if child.tag not in {"p", "ul", "ol"}:
            text = normalise_whitespace(element_text(child))
            if text:
                paragraphs.append(text)
            continue

        text = normalise_whitespace(element_text(child))
        if not text and child.tag == "p":
            continue

        if source is None and text.lower().startswith("source:"):
            source = text.split(":", 1)[1].strip() or None
            continue

        if header_line is None and child.find("em") is not None:
            header_line = text
            continue

        if not metadata_consumed and child.find("strong") is not None and "Casting Time:" in text:
            metadata_fields = parse_metadata_paragraph(child)
            metadata_consumed = True
            continue

        if child.tag in {"ul", "ol"}:
            items = []
            for idx, item in enumerate(child, start=1):
                prefix = "• " if child.tag == "ul" else f"{idx}. "
                items.append(prefix + normalise_whitespace(element_text(item)))
            if items:
                paragraphs.append("\n".join(items))
        else:
            paragraphs.append(text)

    return SpellDetail(source=source, metadata_fields=metadata_fields, paragraphs=paragraphs, header_line=header_line)


def fetch_with_retry(session: requests.Session, url: str, *, retries: int = 3) -> requests.Response:
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=60)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt == retries:
                break
            sleep_for = min(2.0 * attempt, 5.0)
            print(f"Request to {url} failed ({exc}); retrying in {sleep_for:.1f}s…", file=sys.stderr)
            time.sleep(sleep_for)
    assert last_error is not None
    raise last_error


def fetch_spell_list(session: requests.Session) -> List[SpellListing]:
    resp = fetch_with_retry(session, INDEX_URL)
    parser = SpellListParser()
    parser.feed(resp.text)

    listings: List[SpellListing] = []
    for level_idx, tables in parser.tables.items():
        if not tables:
            continue
        table = tables[0]
        for row in table["rows"]:
            if len(row) < 7:
                continue
            name, link = row[0]
            school, _ = row[1]
            spell_lists, _ = row[2]
            casting_time, _ = row[3]
            rng, _ = row[4]
            components, _ = row[5]
            duration, _ = row[6]
            if not name:
                continue
            slug = link or ""
            classes = [entry.strip() for entry in spell_lists.split(",") if entry.strip()]
            listing = SpellListing(
                name=name.strip(),
                slug=slug,
                level=level_idx,
                school=school.strip(),
                classes=classes,
                casting_time=casting_time.strip(),
                range=rng.strip(),
                components=components.strip(),
                duration=duration.strip(),
            )
            listings.append(listing)
    listings.sort(key=lambda item: (item.level, item.name.lower()))
    return listings


def parse_components_field(components_text: str) -> Tuple[List[str], Optional[str]]:
    text = components_text or ""
    detail = None
    if "(" in text and ")" in text:
        base, _, rest = text.partition("(")
        text = base.strip()
        detail = rest.rsplit(")", 1)[0].strip()
    parts = [part.strip().upper() for part in text.replace(";", ",").split(",") if part.strip()]
    return parts, detail


def build_primary_effect(
    *,
    legacy_effect: Optional[dict],
    description: str,
    source: Optional[str],
    classes: List[str],
    header_line: Optional[str],
    tags: Dict[str, bool],
    material_detail: Optional[str],
    url: str,
) -> dict:
    effect = copy.deepcopy(legacy_effect) if legacy_effect else {}
    effect["effect_type"] = "primary"
    if description:
        effect["description"] = description
    effect.setdefault("effect_data", {})
    effect.setdefault("resolution", {"method": "reference", "details": {"url": url}})
    effect.setdefault("repeat", {"count": 1, "interval": "instant"})

    metadata = effect.setdefault("metadata", {})
    if source:
        metadata["source"] = source
    metadata["classes"] = list(classes)
    if header_line:
        metadata["header"] = header_line
    if material_detail:
        metadata["material_detail"] = material_detail
    metadata["reference"] = url
    metadata.setdefault("tags", {}).update({key: bool(value) for key, value in tags.items()})
    return effect


def build_spell_entry(
    listing: SpellListing,
    detail: SpellDetail,
    legacy_entry: Optional[dict],
) -> dict:
    url = f"{BASE_URL}{listing.slug}" if listing.slug else f"{BASE_URL}/spell:{listing.name.lower().replace(' ', '-') }"
    legacy_copy = copy.deepcopy(legacy_entry) if legacy_entry else {}

    metadata_fields = dict(detail.metadata_fields)
    casting_time_raw = metadata_fields.pop("casting_time", None) or listing.casting_time
    duration_raw = metadata_fields.pop("duration", None) or listing.duration
    range_raw = metadata_fields.pop("range", None) or listing.range
    components_raw = metadata_fields.pop("components", None) or listing.components

    ritual = "ritual" in (casting_time_raw or "").lower()
    casting_time_clean = normalise_whitespace(
        casting_time_raw.replace("or Ritual", "").replace("or ritual", "").replace("(ritual)", "")
    ).strip(", ")
    if not casting_time_clean:
        casting_time_clean = listing.casting_time

    concentration = (duration_raw or "").lower().startswith("concentration")
    duration_clean = normalise_whitespace(duration_raw)

    components_list, material_detail = parse_components_field(components_raw)
    comp_tokens = components_list or [part.strip().upper() for part in listing.components.split(",") if part.strip()]

    if metadata_fields:
        for key, value in metadata_fields.items():
            if value:
                UNMAPPED_METADATA_KEYS[key] += 1

    description_text = "\n\n".join(paragraph for paragraph in detail.paragraphs if paragraph)
    if not description_text:
        description_text = f"Refer to the full description at {url}."

    table_components = listing.components
    tags = {
        "ritual": ritual,
        "concentration": concentration,
        "costly_materials": "(C" in table_components,
        "costly_materials_consumed": "(C*)" in table_components,
    }

    primary_effect = build_primary_effect(
        legacy_effect=legacy_copy.get("primary_effect"),
        description=description_text,
        source=detail.source,
        classes=listing.classes,
        header_line=detail.header_line,
        tags=tags,
        material_detail=material_detail,
        url=url,
    )

    entry: Dict[str, object] = {
        "name": listing.name,
        "school": listing.school,
        "casting_time": casting_time_clean,
        "range": normalise_whitespace(range_raw),
        "duration": duration_clean,
        "components": comp_tokens,
        "primary_effect": primary_effect,
    }

    if listing.level > 0:
        entry["level"] = listing.level
    else:
        entry["level"] = 0
        entry["scaling_levels"] = copy.deepcopy(
            legacy_copy.get("scaling_levels", DEFAULT_SCALING_LEVELS)
        )

    entry["modifiers"] = copy.deepcopy(legacy_copy.get("modifiers", []))
    if "secondary_effect" in legacy_copy:
        entry["secondary_effect"] = copy.deepcopy(legacy_copy["secondary_effect"])

    return entry


def load_existing_dataset(path: Path) -> Tuple[Dict[Tuple[str, int], dict], Dict[str, dict], Dict[str, object]]:
    if not path.exists():
        return {}, {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    spells_map: Dict[Tuple[str, int], dict] = {}
    for entry in payload.get("spells", []) or []:
        name = str(entry.get("name", "")).strip().lower()
        level = int(entry.get("level", 0) or 0)
        if name:
            spells_map[(name, level)] = entry
    cantrip_map: Dict[str, dict] = {}
    for entry in payload.get("cantrips", []) or []:
        name = str(entry.get("name", "")).strip().lower()
        if name:
            cantrip_map[name] = entry
    modifiers = payload.get("modifiers") or {}
    return spells_map, cantrip_map, modifiers


def write_dataset(
    *,
    output_path: Path,
    spells: List[dict],
    cantrips: List[dict],
    modifiers: Dict[str, object],
    source_url: str,
) -> None:
    payload = {
        "metadata": {
            "source": source_url.replace("/noredirect/true/do=print", ""),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "spell_count": len(spells),
            "cantrip_count": len(cantrips),
        },
        "spells": spells,
        "cantrips": cantrips,
        "modifiers": modifiers,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_dataset_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    placeholder = {
        "metadata": {
            "source": INDEX_URL.replace("/noredirect/true/do=print", ""),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "spell_count": 0,
            "cantrip_count": 0,
        },
        "spells": [],
        "cantrips": [],
        "modifiers": {},
    }
    path.write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update spellbook.json from the Wikidot 2024 spell list.")
    parser.add_argument("--output", default="spellbook.json", help="Destination JSON file (default: spellbook.json)")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between page fetches in seconds (default: 0.15)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).resolve()
    ensure_dataset_file(output_path)
    legacy_spells, legacy_cantrips, legacy_modifiers = load_existing_dataset(output_path)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("Fetching spell index…", file=sys.stderr)
    listings = fetch_spell_list(session)
    total = len(listings)
    print(f"Found {total} spells and cantrips", file=sys.stderr)

    spells: List[dict] = []
    cantrips: List[dict] = []

    for idx, listing in enumerate(listings, start=1):
        slug_display = listing.slug or listing.name
        print(f"[{idx}/{total}] Fetching {listing.name} ({slug_display})", file=sys.stderr)
        detail_url = f"{BASE_URL}{listing.slug}{DETAIL_SUFFIX}" if listing.slug else None
        if detail_url is None:
            detail_url = f"{BASE_URL}/spell:{listing.name.lower().replace(' ', '-')}{DETAIL_SUFFIX}"
        resp = fetch_with_retry(session, detail_url)
        detail = parse_spell_detail(resp.text)

        key = (listing.name.strip().lower(), listing.level)
        if listing.level == 0:
            legacy_entry = legacy_cantrips.get(key[0])
        else:
            legacy_entry = legacy_spells.get(key)

        entry = build_spell_entry(listing, detail, legacy_entry)
        if listing.level == 0:
            cantrips.append(entry)
        else:
            spells.append(entry)

        if args.delay:
            time.sleep(max(args.delay, 0.0))

    spells.sort(key=lambda item: (int(item.get("level", 0) or 0), str(item.get("name", "")).lower()))
    cantrips.sort(key=lambda item: str(item.get("name", "")).lower())

    write_dataset(
        output_path=output_path,
        spells=spells,
        cantrips=cantrips,
        modifiers=legacy_modifiers,
        source_url=INDEX_URL,
    )
    print(f"Wrote dataset to {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
