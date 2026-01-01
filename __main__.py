"""Module entry point that launches the PySide6 GUI."""

import sys

def main() -> int:
    """Start the graphical application and return its exit code."""

    try:
        from gui.app import main as launch_gui
    except ModuleNotFoundError as exc:
        # Most common: the user is running outside the venv.
        if exc.name and exc.name.startswith("PySide6"):
            print(
                "PySide6 is not installed in the active Python environment.\n"
                "Install dependencies and try again:\n\n"
                "  pip install -r requirements.txt\n\n"
                "Or make sure you're using the project's venv interpreter, e.g.:\n\n"
                "  .venv/bin/python -m gui.app\n"
            )
            return 1
        raise

    return launch_gui()


if __name__ == "__main__":
    sys.exit(main())