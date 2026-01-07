# UI Theme & Styling Guide

Living Scroll uses a centralized PySide6/Qt stylesheet system to ensure a consistent, modern dark theme across all modules.

## Central Theme File
The core theme definition is located at:
`gui/theme.py`

This file exports `DARK_THEME_STYLESHEET`, which is applied to the global `QApplication` instance in `gui/app.py`.

### Structure
The theme is broken down into python string constants for maintainability:
- `_CORE_STYLES`: Main window backgrounds, fonts.
- `_INPUT_STYLES`: Inputs, Buttons, Dropdowns.
- `_CHECKBOX_STYLES`: Checkboxes and Radio buttons (including custom indicators).
- `_SCROLL_LIST_STYLES`: ListWidgets, Tables, ScrollAreas.
- `_SCROLLBAR_STYLES`: Custom scrollbar width and colors.
- `_CUSTOM_WIDGET_STYLES`: Module-specific widgets like `TileButton` or `CustomTitleBar`.

## How to Customize
To change colors or widget appearances, edit `gui/theme.py`.

### Changing Colors
Modify the `COLORS` dictionary at the top of the file:
```python
COLORS = {
    "bg_main": "#1e1e1e",
    "accent_blue": "#007acc", # Change this to your preferred accent
    ...
}
```

### Adding New Widget Styles
1. Define a new style block string (e.g., `_MY_WIDGET_STYLE = "..."`).
2. Add it to the list in `"\n".join([...])` at the bottom of the file.

## Best Practices
- **Avoid Ad-Hoc Styling:** Do not use `widget.setStyleSheet("...")` in individual dialog code unless absolutely necessary for unique, one-off behavior.
- **Use Class Selectors:** Assign a class property to widgets if they need special styling (e.g., `btn.setProperty("class", "TileButton")`) and target them in `theme.py` using `QPushButton[class="TileButton"]`.
- **Test Globally:** Changes in `theme.py` affect the entire application.
