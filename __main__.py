"""Module entry point that launches the PySide6 GUI."""

import sys

from gui import main as launch_gui


def main() -> int:
    """Start the graphical application and return its exit code."""

    return launch_gui()


if __name__ == "__main__":
    sys.exit(main())