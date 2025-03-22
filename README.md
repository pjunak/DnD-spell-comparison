
# Plotting D&D 5e spells

This project lets you visualize the probability distributions of D&D spells and cantrips as a function of spell (or effective) level. It supports comparing multiple spells or cantrips on the same graph.

## Features

- **Single Spell Plotting:** 
  View the probability distribution for a chosen spell (or cantrip) across its available levels.
- **Comparison Mode:** 
  Compare up to 3 spells (or cantrips) that share the same category (spells or cantrips).
  Each common level is plotted with colors indicating the level while each spell uses a distinct line style.
  The legends are interactive: click on a legend entry to isolate that level or spell.
- **Interactive Annotations:**
  Hover over a plot point to view detailed information for that value (probability, cumulative probabilities above and below).

## How to Use

1. **Run the Program:**
   Execute the main module (e.g. run `python __main__.py` from the project directory).
2. **Main Menu Options:**

   - **S:** Plot a single spell (or cantrip).You will be prompted to choose from a numbered list.
   - **C:** Compare multiple spells/cantrips.First choose whether to compare spells or cantrips, then enter the selection numbers separated by spaces.
   - **M:** Change the spellcasting modifier.
   - **B:** Return up.
   - **X:** Exit the program.
3. **Interactivity:**
   In the plots, click the legend entries to isolate a specific spell or level.
   Hover to see numeric details in an annotation.

## Current State

- The project uses matplotlib for plotting and supports interactive legend clicks.
- The probability distributions are computed using custom dice roll combination functions.
- Spells and cantrips are defined in separate modules under `magic/`.
- Only works for most standard spells, spells with multiple damaging effects are yet to be implemented.

## Requirements

- Python 3.x
- matplotlib
- numpy

Install required packages (if not already installed):

```bash
pip install matplotlib numpy
```

## License

This project is provided as-is for educational and personal use.
