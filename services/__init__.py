"""High-level services for importing/exporting data and shared business logic.

Note: Core logic has moved to `modules/`. This package remains for specific shared services
like `class_options` and `rules_config` until they are fully modularized.
"""

# The following were moved to modules/ but kept here for potential legacy access
# (though ideally code should import directly from modules/)
# from modules.compendium.service import Compendium, DEFAULT_COMPENDIUM_PATH

__all__ = []
