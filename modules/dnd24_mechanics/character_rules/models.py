"""Dataclasses representing character rule definitions and evaluation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FeatureOptionChoice:
    """A single selectable option within a feature option group."""

    value: str
    label: str
    description: Optional[str] = None
    enabled: bool = True


@dataclass(frozen=True)
class FeatureOptionGroup:
    """Represents a collection of mutually exclusive options for a feature."""

    key: str
    label: str
    description: str = ""
    min_level: int = 1
    choices: List[FeatureOptionChoice] = field(default_factory=list)
    required: bool = False
    default: Optional[str] = None
    width: Optional[int] = None


@dataclass(frozen=True)
class ClassFeatureRule:
    """Defines when a class/subclass feature becomes available."""

    key: str
    label: str
    class_name: str
    min_level: int = 1
    subclass_name: Optional[str] = None
    description: str = ""
    effect_data: Dict[str, Any] = field(default_factory=dict)
    options: List[FeatureOptionGroup] = field(default_factory=list)


@dataclass(frozen=True)
class CharacterRuleSnapshot:
    """Result of evaluating all rules for a specific character sheet."""

    features: List[ClassFeatureRule]
    option_groups: List[FeatureOptionGroup]
    selections: Dict[str, str]


__all__ = [
    "FeatureOptionChoice",
    "FeatureOptionGroup",
    "ClassFeatureRule",
    "CharacterRuleSnapshot",
]
