"""Backend helpers for probability, datasets, and plotting."""

from . import calculations, dices

try:
	from . import plotting
except ModuleNotFoundError:
	# Optional dependency (matplotlib) may be absent in minimal environments.
	plotting = None  # type: ignore[assignment]

__all__ = ["calculations", "dices", "plotting"]
