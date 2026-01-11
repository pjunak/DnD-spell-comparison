"""Character sheet import/export helpers."""

from .json_adapter import CharacterPackage, load_character_package, save_character_package

try:
    from .pdf_adapter import load_character_pdf, save_character_pdf
except ModuleNotFoundError:
    # Optional dependency (PyMuPDF / fitz) may be absent in minimal environments.
    def load_character_pdf(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise ModuleNotFoundError("Optional dependency 'fitz' is required for PDF import/export")

    def save_character_pdf(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise ModuleNotFoundError("Optional dependency 'fitz' is required for PDF import/export")

__all__ = [
    "CharacterPackage",
    "load_character_package",
    "save_character_package",
    "load_character_pdf",
    "save_character_pdf",
]
