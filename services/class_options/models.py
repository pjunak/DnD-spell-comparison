"""Dataclasses for structured class option selections (invocations, boons, etc.)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ClassOptionChoice:
    """Single selectable option tied to a class feature progression."""

    value: str
    label: str
    description: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassOptionGroup:
    """Collection of related class options with a shared pick limit."""

    key: str
    label: str
    class_name: str
    min_level: int
    max_choices: int
    choices: List[ClassOptionChoice] = field(default_factory=list)
    helper_text: str = ""


@dataclass(frozen=True)
class ClassOptionSnapshot:
    """Computed view of class option groups plus resolved selections."""

    groups: List[ClassOptionGroup]
    selections: Dict[str, List[str]]


__all__ = ["ClassOptionChoice", "ClassOptionGroup", "ClassOptionSnapshot"]
