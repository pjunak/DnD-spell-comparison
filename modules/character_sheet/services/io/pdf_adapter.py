"""PDF import / export helpers for SpellGraphix character sheets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import fitz

from modules.character_sheet.model import ABILITY_NAMES, CharacterSheet, character_sheet_from_dict, character_sheet_to_dict

from .json_adapter import CharacterPackage


_ROOT_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_TEMPLATE = _ROOT_DIR / "Assets" / "DnD_2024_Character-Sheet.pdf"
_EMBEDDED_FILE_NAME = "spellgraphix-character.json"


@dataclass(frozen=True)
class _RectOffset:
    left: float
    top: float
    right: float
    bottom: float


class _PdfWriter:
    """Utility wrapper that writes relative to anchor labels inside the template."""

    def __init__(self, page: fitz.Page):
        self._page = page
        self._anchors: Dict[tuple[str, int], Optional[fitz.Rect]] = {}

    def _anchor(self, label: str, occurrence: int = 0) -> Optional[fitz.Rect]:
        key = (label.lower(), occurrence)
        if key not in self._anchors:
            rects = list(self._page.search_for(label))
            if not rects:
                self._anchors[key] = None
            else:
                rects.sort(key=lambda rect: (rect.y0, rect.x0))
                index = min(max(occurrence, 0), len(rects) - 1)
                self._anchors[key] = rects[index]
        return self._anchors[key]

    def write_below(
        self,
        label: str,
        value: str,
        *,
        width: float,
        height: float,
        dx: float = 0.0,
        dy: float = 2.0,
        occurrence: int = 0,
        font_size: float = 10.0,
        align: int = fitz.TEXT_ALIGN_LEFT,
    ) -> bool:
        text = _clean_text(value)
        if text is None:
            return False
        anchor = self._anchor(label, occurrence)
        if not anchor:
            return False
        rect = fitz.Rect(
            anchor.x0 + dx,
            anchor.y1 + dy,
            anchor.x0 + dx + width,
            anchor.y1 + dy + height,
        )
        self._page.insert_textbox(rect, text, fontname="helv", fontsize=font_size, align=align, color=(0, 0, 0))
        return True

    def write_relative(
        self,
        label: str,
        value: str,
        offsets: _RectOffset,
        *,
        occurrence: int = 0,
        font_size: float = 10.0,
        align: int = fitz.TEXT_ALIGN_LEFT,
    ) -> bool:
        text = _clean_text(value)
        if text is None:
            return False
        anchor = self._anchor(label, occurrence)
        if not anchor:
            return False
        rect = fitz.Rect(
            anchor.x0 + offsets.left,
            anchor.y0 + offsets.top,
            anchor.x0 + offsets.right,
            anchor.y0 + offsets.bottom,
        )
        self._page.insert_textbox(rect, text, fontname="helv", fontsize=font_size, align=align, color=(0, 0, 0))
        return True


def save_character_pdf(
    output_path: Path | str,
    sheet: CharacterSheet,
    modifiers: Dict[str, bool],
    *,
    template_path: Optional[Path | str] = None,
) -> Path:
    """Render a filled character sheet PDF and embed the source data for lossless import."""

    template = _resolve_template(template_path)
    destination = Path(output_path)

    doc = fitz.open(template)
    try:
        page = doc[0]
        writer = _PdfWriter(page)
        _render_identity(writer, sheet)
        _render_combat(writer, sheet)
        _render_abilities(writer, sheet)
        _render_proficiencies(writer, sheet)

        payload = _package_payload(sheet, modifiers)
        _embed_payload(doc, payload)
        _set_metadata(doc, sheet)

        doc.save(str(destination))
    finally:
        doc.close()

    return destination


def load_character_pdf(path_like: Path | str) -> CharacterPackage:
    """Load a PDF that was previously exported by SpellGraphix."""

    path = Path(path_like)
    doc = fitz.open(path)
    try:
        data = _extract_payload(doc)
    finally:
        doc.close()

    payload = json.loads(data.decode("utf-8"))
    sheet_payload = payload.get("character_sheet", {}) or {}
    modifiers_payload = payload.get("modifiers", {}) or {}

    sheet = character_sheet_from_dict(sheet_payload)
    modifiers: Dict[str, bool] = {str(key): bool(value) for key, value in modifiers_payload.items()}
    return CharacterPackage(sheet=sheet, modifiers=modifiers)


def _render_identity(writer: _PdfWriter, sheet: CharacterSheet) -> None:
    identity = sheet.identity
    writer.write_below("character name", identity.name, width=260, height=16, font_size=12)
    writer.write_below("background", identity.background, width=200, height=12)
    writer.write_below("species", identity.ancestry, width=140, height=12)
    writer.write_below("subclass", _primary_subclass(identity), width=160, height=12)
    writer.write_below("class", _class_summary(identity), width=240, height=12)
    writer.write_below("level", str(identity.level or ""), width=60, height=12, align=fitz.TEXT_ALIGN_CENTER)
    writer.write_below("xp", str(identity.experience or ""), width=90, height=12, align=fitz.TEXT_ALIGN_CENTER)

    if identity.player:
        writer.write_below("character name", f"Player: {identity.player}", width=260, height=12, dy=18, font_size=8)
    if identity.alignment:
        writer.write_below("species", f"Alignment: {identity.alignment}", width=160, height=10, dy=14, font_size=8)


def _render_combat(writer: _PdfWriter, sheet: CharacterSheet) -> None:
    combat = sheet.combat
    writer.write_below(
        "ARMOR",
        str(combat.armor_class or ""),
        width=70,
        height=24,
        dy=20,
        font_size=16,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "PROFICIENCY",
        _format_bonus(sheet.proficiencies.proficiency_bonus),
        width=80,
        height=14,
        dy=12,
        font_size=12,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "INITIATIVE",
        _format_bonus(combat.initiative_bonus),
        width=80,
        height=12,
        dy=10,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "SPEED",
        _speed_text(combat.speed_ft),
        width=80,
        height=12,
        dy=10,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "PASSIVE",
        str(_passive_perception(sheet)),
        width=100,
        height=12,
        dy=10,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "current",
        str(combat.current_hp),
        width=110,
        height=16,
        dy=8,
        font_size=12,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "max",
        str(combat.max_hp),
        width=90,
        height=16,
        dy=8,
        font_size=12,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "temp",
        str(combat.temp_hp or ""),
        width=90,
        height=14,
        dy=8,
        font_size=12,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "DICE",
        combat.hit_dice,
        width=100,
        height=14,
        dy=8,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "successes",
        str(combat.death_save_successes),
        width=60,
        height=12,
        dy=8,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    writer.write_below(
        "failures",
        str(combat.death_save_failures),
        width=60,
        height=12,
        dy=8,
        align=fitz.TEXT_ALIGN_CENTER,
    )


_ABILITY_SCORE_OFFSET = _RectOffset(-6, 18, 58, 58)
_ABILITY_MOD_OFFSET = _RectOffset(-6, 66, 58, 88)
_ABILITY_LABELS = {
    "STR": "STRENGTH",
    "DEX": "DEXTERITY",
    "CON": "CONSTITUTION",
    "INT": "INTELLIGENCE",
    "WIS": "WISDOM",
    "CHA": "CHARISMA",
}


def _render_abilities(writer: _PdfWriter, sheet: CharacterSheet) -> None:
    for ability in ABILITY_NAMES:
        label = _ABILITY_LABELS.get(ability)
        block = sheet.abilities.get(ability)
        if not label or not block:
            continue
        writer.write_relative(
            label,
            str(block.score),
            _ABILITY_SCORE_OFFSET,
            font_size=16,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        writer.write_relative(
            label,
            _format_bonus(block.effective_modifier()),
            _ABILITY_MOD_OFFSET,
            font_size=11,
            align=fitz.TEXT_ALIGN_CENTER,
        )


def _render_proficiencies(writer: _PdfWriter, sheet: CharacterSheet) -> None:
    profs = sheet.proficiencies
    writer.write_below(
        "armor",
        ", ".join(profs.armor),
        width=260,
        height=12,
        dy=8,
        occurrence=1,
    )
    writer.write_below(
        "weapons",
        ", ".join(profs.weapons),
        width=260,
        height=12,
        dy=8,
    )
    writer.write_below(
        "tools",
        ", ".join(profs.tools),
        width=260,
        height=12,
        dy=8,
    )


def _class_summary(identity) -> str:
    parts = []
    for entry in identity.classes:
        if entry.subclass:
            parts.append(f"{entry.name} {entry.level} ({entry.subclass})")
        else:
            parts.append(f"{entry.name} {entry.level}")
    return ", ".join(filter(None, parts))


def _primary_subclass(identity) -> str:
    for entry in identity.classes:
        if entry.subclass:
            return entry.subclass
    return ""


def _passive_perception(sheet: CharacterSheet) -> int:
    note = sheet.notes.get("passive_perception") if sheet.notes else None
    if isinstance(note, int):
        return note
    if isinstance(note, str) and note.strip().isdigit():
        return int(note.strip())
    wisdom = sheet.abilities.get("WIS")
    modifier = wisdom.effective_modifier() if wisdom else 0
    return 10 + modifier


def _format_bonus(value: Optional[int]) -> str:
    if value is None:
        return ""
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return ""
    sign = "+" if numeric >= 0 else ""
    return f"{sign}{numeric}"


def _speed_text(speed_ft: int) -> str:
    if not speed_ft:
        return ""
    return f"{speed_ft} ft"


def _package_payload(sheet: CharacterSheet, modifiers: Dict[str, bool]) -> bytes:
    payload = {
        "character_sheet": character_sheet_to_dict(sheet),
        "modifiers": dict(modifiers),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _embed_payload(doc: fitz.Document, payload: bytes) -> None:
    for name in list(doc.embfile_names()):
        if name == _EMBEDDED_FILE_NAME:
            doc.embfile_del(name)
    doc.embfile_add(_EMBEDDED_FILE_NAME, payload, filename="character.json")


def _extract_payload(doc: fitz.Document) -> bytes:
    for name in doc.embfile_names():
        if name == _EMBEDDED_FILE_NAME:
            return doc.embfile_get(name)
    raise ValueError("PDF does not contain SpellGraphix character data")


def _resolve_template(path: Optional[Path | str]) -> Path:
    template = Path(path) if path else _DEFAULT_TEMPLATE
    if not template.exists():
        raise FileNotFoundError(f"PDF template not found: {template}")
    return template


def _set_metadata(doc: fitz.Document, sheet: CharacterSheet) -> None:
    metadata = dict(doc.metadata or {})
    metadata.setdefault("producer", "SpellGraphix")
    metadata["title"] = sheet.identity.name or "SpellGraphix Character Sheet"
    metadata["keywords"] = "SpellGraphix Character"
    doc.set_metadata(metadata)


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = ["save_character_pdf", "load_character_pdf"]
