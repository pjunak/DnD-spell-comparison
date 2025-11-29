"""Shared test configuration (headless matplotlib/Qt backends)."""

import os
import warnings

import matplotlib

matplotlib.use("Agg", force=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
warnings.simplefilter("ignore", ResourceWarning)
