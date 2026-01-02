"""Shared test configuration (headless matplotlib/Qt backends)."""

import os
import warnings

try:
	import matplotlib

	matplotlib.use("Agg", force=True)
except ModuleNotFoundError:
	# Some environments run the non-plotting tests without matplotlib installed.
	# Keep the test package importable so unrelated test modules can still run.
	pass
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.simplefilter("ignore", ResourceWarning)
