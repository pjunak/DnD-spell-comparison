"""GUI package for the SpellGraphix application."""

from __future__ import annotations


def main() -> int:
	"""Launch the GUI.

	Imported lazily to avoid side effects when running modules like `python -m gui.app`.
	"""

	from .app import main as _main
	return _main()


__all__ = ["main"]
