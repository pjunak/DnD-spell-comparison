"""Matplotlib helpers for plotting spell damage distributions."""

from __future__ import annotations

from bisect import bisect_left

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.figure import Figure

from modules.core.services import calculations

LEVEL_DEFAULT = 9
MAX_COMPARE_SPELLS = 9
VISIBLE_LINE_ALPHA_THRESHOLD = 0.25
LEVEL_LINESTYLES = [
    "-",
    "--",
    ":",
    "-.",
    (0, (5, 2)),
    (0, (3, 1, 1, 1)),
    (0, (1, 1)),
    (0, (5, 1, 1, 1)),
    (0, (3, 5, 1, 5)),
]
LEVEL_MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "+"]


def _underline_text(text: str) -> str:
    """Return the text with a combining underline applied to each non-space character."""

    if not text:
        return text
    return "".join((char + "\u0332") if char.strip() else char for char in text)


class InteractiveAnnotator:
    """Efficient hover annotations for matplotlib plots."""

    _NEIGHBOR_WINDOW = 3  # Examine +/- window around the x position in sorted data

    def __init__(self, ax, fig, line_data, value_name="Damage", all_points=None, line_labels=None):
        self.ax = ax
        self.fig = fig
        self.line_data = line_data
        self.value_name = value_name
        self._transform = ax.transData
        self._labels = line_labels or {}

        # Precompute sorted x/y arrays per line for fast bisect searches
        point_map: dict = {}
        if all_points is not None:
            for line, x, y in all_points:
                point_map.setdefault(line, []).append((x, y))

        self._line_points = []
        for line, (x_vals, y_vals) in line_data.items():
            if line in point_map:
                samples = point_map[line]
            else:
                samples = list(zip(x_vals, y_vals))
            if not samples:
                continue
            samples.sort(key=lambda pair: pair[0])
            xs, ys = zip(*samples)
            self._line_points.append({
                "line": line,
                "x": xs,
                "y": ys,
                "label": self._labels.get(line),
            })

        self.annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="lightyellow"),
            arrowprops=dict(arrowstyle="->"),
        )
        self.annot.set_visible(False)

        self.fig.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def update_annotation(self, line, x, y, label_override=None):
        """Update annotation text and position for the given point."""
        self.annot.xy = (x, y)
        
        # Calculate cumulative probabilities
        x_vals, y_vals = self.line_data[line]
        p_greater = sum(prob for val, prob in zip(x_vals, y_vals) if val > x)
        p_less = sum(prob for val, prob in zip(x_vals, y_vals) if val < x)
        
        x_disp = round(x)
        label = label_override or self._labels.get(line) or line.get_label() or ""
        if label.startswith("_child") or label.startswith("_line"):
            label = label_override or self._labels.get(line) or ""
        segments = []
        if label:
            segments.append(f"{label}\n")
        segments.append(f"{self.value_name}: {x_disp}\n")
        segments.append(f"Probability: {y:.3%}\n")
        segments.append(f"P(>{x_disp}): {p_greater:.3%}\n")
        segments.append(f"P(<{x_disp}): {p_less:.3%}")
        self.annot.set_text("".join(segments))
        patch = self.annot.get_bbox_patch()
        if patch is not None:
            patch.set_facecolor("lightyellow")
            patch.set_alpha(0.9)

    def on_hover(self, event):
        """Handle mouse motion events to show/hide annotation."""
        vis = self.annot.get_visible()
        
        if event.inaxes != self.ax:
            if vis:
                self.annot.set_visible(False)
                self.fig.canvas.draw_idle()
            return
            
        if event.xdata is None or event.ydata is None:
            return

        event_display = self._transform.transform((event.xdata, event.ydata))

        min_dist = float("inf")
        closest_point = None

        for entry in self._line_points:
            line = entry["line"]
            if not line.get_visible():
                continue
            alpha = line.get_alpha()
            if alpha is not None and alpha <= VISIBLE_LINE_ALPHA_THRESHOLD:
                continue

            xs = entry["x"]
            ys = entry["y"]
            if not xs:
                continue

            idx = bisect_left(xs, event.xdata)
            start = max(0, idx - self._NEIGHBOR_WINDOW)
            end = min(len(xs), idx + self._NEIGHBOR_WINDOW + 1)

            for pos in range(start, end):
                x = xs[pos]
                y = ys[pos]
                point_display = self._transform.transform((x, y))
                dist = ((point_display[0] - event_display[0]) ** 2 +
                        (point_display[1] - event_display[1]) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    closest_point = (line, x, y, entry.get("label"))

        if closest_point:
            line, x, y, label_override = closest_point
            self.update_annotation(line, x, y, label_override=label_override)
            self.annot.set_visible(True)
            self.fig.canvas.draw_idle()
        elif vis:
            self.annot.set_visible(False)
            self.fig.canvas.draw_idle()


def extract_effect_params(spell):
    """
    Extracts effect parameters from a spell dictionary.

    Args:
        spell_data (dict): Dictionary containing spell information.

    Returns:
        tuple: A tuple containing (dice_count, die_sides, modifier, damage_type).
    """
    effects = spell.get("effects", [])
    primary = None
    for eff in effects:
        if eff.get("effect_type", "") == "primary":
            primary = eff
            break
    if primary is None and effects:
        primary = effects[0]
    damage = primary.get("effect_data", {}).get("damage", {}) if primary else {}
    if not damage:
        return None

    base = damage.get("base") or {}
    scaling = damage.get("scaling") or {}

    start_rolls = int(base.get("dice") or 0)
    initial_die = int(base.get("die") or 0)
    add_rolls = int(scaling.get("dice_per_slot") or 0)
    additional_die = int(scaling.get("die") or 0)
    use_modifier = bool(damage.get("use_modifier", False))
    constant = int(damage.get("constant") or 0)

    if start_rolls <= 0:
        return None

    if start_rolls > 0 and initial_die <= 0:
        initial_die = 6
    if add_rolls > 0 and additional_die <= 0:
        additional_dice_fallback = initial_die if initial_die > 0 else 6
        additional_die = additional_dice_fallback

    value_name = str(damage.get("type", "Damage")).replace("_", " ").title()
    return {
        "start_rolls": start_rolls,
        "initial_dice_value": initial_die,
        "add_rolls": add_rolls,
        "additional_dice_value": additional_die,
        "use_modifier": use_modifier,
        "constant_per_die": constant,
        "valueName": value_name,
    }


def plot_spell(spell, mod, spell_full_name):
    params = extract_effect_params(spell)
    if params is None:
        raise ValueError(f"{spell_full_name} has no damage values to plot.")
    lvl = spell.get("level", 1)
    level_range = list(range(1, 5)) if lvl == 0 else list(range(lvl, LEVEL_DEFAULT + 1))
    level_distributions = {}
    for level in level_range:
        lvl_param = level if lvl == 0 else (level - lvl + 1)
        distribution = calculations.chain_spell_distribution(
            start_rolls=params["start_rolls"],
            add_rolls=params["add_rolls"],
            initial_dice_value=params["initial_dice_value"],
            additional_dice_value=params["additional_dice_value"],
            modifier=mod,
            levels=lvl_param,
            constant_per_die=params["constant_per_die"],
        )
        level_distributions[level] = distribution
    title = f"{spell_full_name} {params['valueName']} by levels with +{mod} modifier"
    fig, ax = plt.subplots()
    fig.suptitle(title)
    ax.set_xlabel(params["valueName"])
    ax.set_ylabel("Probability")
    plt.text(0.5, 1.02, "Click to isolate", transform=ax.transAxes, ha="center", fontsize=10, color="gray")
    line_data = {}
    line_labels = {}
    all_points = []
    plots = []
    for level, dist in sorted(level_distributions.items()):
        sp = sorted([(x, y) for x, y in dist.items() if y > 0], key=lambda p: p[0])
        if not sp:
            continue
        x_vals, y_vals = zip(*sp)
        (line,) = ax.plot(x_vals, y_vals, label=f"Level {level}", marker="o")
        plots.append(line)
        line_data[line] = (x_vals, y_vals)
        line_labels[line] = f"Level {level}"
        for x, y in zip(x_vals, y_vals):
            all_points.append((line, x, y))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=1))
    from matplotlib.lines import Line2D

    dummy = Line2D([], [], linestyle="", color="none")
    handles, labels = ax.get_legend_handles_labels()
    handles.append(dummy)
    labels.append("Click to isolate")
    leg = ax.legend(handles, labels, title="Spell Level", loc="upper right", fancybox=True, shadow=True)
    texts = leg.get_texts()
    if texts:
        texts[-1].set_color("gray")
        texts[-1].set_fontstyle("italic")
    legend_objs = leg.get_lines()[:-1]
    legend_label_texts = leg.get_texts()[:-1]
    legend_base_labels = [t.get_text() for t in legend_label_texts]
    for obj in legend_objs + leg.get_texts()[:-1]:
        obj.set_picker(5)
    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}

    selected_idx = None

    def _highlight_legend(idx: int | None):
        nonlocal selected_idx
        selected_idx = idx
        for i, text in enumerate(legend_label_texts):
            active = idx is not None and i == idx
            base = legend_base_labels[i]
            text.set_text(_underline_text(base) if active else base)
            text.set_fontweight("bold" if active else "normal")
            text.set_color("#000000")
            line = legend_objs[i]
            line.set_linewidth(3 if active else 1.5)

    def on_pick(event):
        if event.artist in legend_objs:
            idx = legend_objs.index(event.artist)
        elif event.artist in leg.get_texts()[:-1]:
            idx = leg.get_texts()[:-1].index(event.artist)
        else:
            return
        clicked_line = plots[idx]
        if clicked_line.get_alpha() == 1.0 and all(
            other.get_alpha() < 1.0 for i, other in enumerate(plots) if i != idx
        ):
            for line in plots:
                line.set_alpha(original_alphas[line])
            _highlight_legend(None)
        else:
            for i, line in enumerate(plots):
                line.set_alpha(1.0 if i == idx else 0.1)
            _highlight_legend(idx)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("pick_event", on_pick)
    # Store reference to prevent garbage collection
    annotator = InteractiveAnnotator(
        ax,
        fig,
        line_data,
        value_name=params["valueName"],
        all_points=all_points,
        line_labels=line_labels,
    )
    persistent = getattr(fig.canvas, "_persistent_callbacks", [])
    persistent.append(annotator)
    setattr(fig.canvas, "_persistent_callbacks", persistent)
    if not plots:
        plt.close(fig)
        raise ValueError(f"{spell_full_name} has no damage distribution across the available levels.")
    return fig


def compare_spells(selected_spells, mod):
    from matplotlib.lines import Line2D

    is_cantrip = [s.get("level", 1) == 0 for s in selected_spells]
    if not (all(is_cantrip) or (not any(is_cantrip))):
        raise ValueError("Cannot compare a mix of cantrips and leveled spells.")
    if len(selected_spells) < 2 or len(selected_spells) > MAX_COMPARE_SPELLS:
        raise ValueError(f"Select between 2 and {MAX_COMPARE_SPELLS} spells for comparison.")

    prepared_params = []
    missing_damage = []
    for spell in selected_spells:
        params = extract_effect_params(spell)
        if params is None:
            missing_damage.append(spell.get("name", "Unknown"))
        prepared_params.append(params)
    if missing_damage:
        raise ValueError("Cannot compare spells without damage values: " + ", ".join(missing_damage))

    spell_levels = []
    for s in selected_spells:
        if s.get("level", 1) == 0:
            available = set(range(1, 5))
        else:
            base = s.get("level", 1)
            available = set(range(base, 10))
        spell_levels.append(available)
    union_levels = sorted(set().union(*spell_levels))
    if not union_levels:
        raise ValueError("No common levels available for the selected spells.")
    num_spells = len(selected_spells)
    cmap = plt.get_cmap("tab10")
    spell_colors = [cmap(i % cmap.N) for i in range(num_spells)]
    level_styles = {lvl: LEVEL_LINESTYLES[idx % len(LEVEL_LINESTYLES)] for idx, lvl in enumerate(union_levels)}
    level_markers = {lvl: LEVEL_MARKERS[idx % len(LEVEL_MARKERS)] for idx, lvl in enumerate(union_levels)}
    fig, ax = plt.subplots()
    header_names = [s.get("name", "Unknown") for s in selected_spells]
    title = "Comparison: " + ", ".join(header_names) + f" with +{mod} modifier"
    fig.suptitle(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Probability")
    line_data = {}
    line_labels = {}
    all_points = []
    plots = []
    level_lines = {lvl: [] for lvl in union_levels}
    spell_lines = {j: [] for j in range(num_spells)}
    for lvl in union_levels:
        for j, s in enumerate(selected_spells):
            if s.get("level", 1) == 0:
                if lvl not in range(1, 5):
                    continue
                lvl_param = lvl
            else:
                base = s.get("level", 1)
                if lvl < base:
                    continue
                lvl_param = lvl - base + 1
            params = prepared_params[j]
            distribution = calculations.chain_spell_distribution(
                start_rolls=params["start_rolls"],
                add_rolls=params["add_rolls"],
                initial_dice_value=params["initial_dice_value"],
                additional_dice_value=params["additional_dice_value"],
                modifier=mod,
                levels=lvl_param,
                constant_per_die=params["constant_per_die"],
            )
            filtered = sorted([(x, y) for x, y in distribution.items() if y > 0], key=lambda p: p[0])
            if not filtered:
                continue
            x_vals, y_vals = zip(*filtered)
            style = level_styles[lvl]
            marker = level_markers[lvl]
            color = spell_colors[j]
            (line,) = ax.plot(
                x_vals,
                y_vals,
                linestyle=style,
                marker=marker,
                color=color,
            )
            level_lines[lvl].append(line)
            spell_lines[j].append(line)
            plots.append(line)
            line_data[line] = (x_vals, y_vals)
            spell_name = s.get("name", "Spell")
            if is_cantrip[0]:
                label_suffix = f"Player lvl {lvl}"
            else:
                label_suffix = f"Spell lvl {lvl}"
            line_labels[line] = f"{spell_name} ({label_suffix})"
            for x, y in zip(x_vals, y_vals):
                all_points.append((line, x, y))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=1))
    level_handles = []
    level_labels = []
    for lvl in union_levels:
        if is_cantrip[0]:
            mapping = {1: "<5", 2: "5", 3: "11", 4: "17"}
            label = f"Player Level {mapping.get(lvl, lvl)}"
        else:
            label = f"Spell Level {lvl}"
        handle = Line2D([], [], color="#d0d0d0", lw=2, linestyle=level_styles[lvl], marker=level_markers[lvl])
        level_handles.append(handle)
        level_labels.append(label)
    dummy1 = Line2D([], [], linestyle="", color="none")
    level_handles.append(dummy1)
    level_labels.append("Click to isolate level")
    level_leg = ax.legend(level_handles, level_labels, title="Level", loc="upper right", fancybox=True, shadow=True)
    level_lines_artists = level_leg.get_lines()[:-1]
    level_text_artists = level_leg.get_texts()[:-1]
    level_base_labels = [text.get_text() for text in level_text_artists]
    level_instruction = level_leg.get_texts()[-1] if level_leg.get_texts() else None
    if level_instruction is not None:
        level_instruction.set_color("gray")
        level_instruction.set_fontstyle("italic")
    for obj in list(level_lines_artists) + list(level_text_artists):
        obj.set_picker(5)
    spell_handles = []
    spell_labels = []
    for i, s in enumerate(selected_spells):
        color = spell_colors[i]
        handle = Line2D([], [], linestyle="-", marker="o", color=color, lw=2)
        spell_handles.append(handle)
        spell_labels.append(s.get("name", "Unknown"))
    spell_leg = ax.legend(
        spell_handles,
        spell_labels,
        title="Spells",
        loc="upper right",
        bbox_to_anchor=(0.78, 1.0),
        borderaxespad=0.3,
        fancybox=True,
        shadow=True,
    )
    spell_line_artists = spell_leg.get_lines()
    spell_text_artists = spell_leg.get_texts()
    spell_base_labels = [text.get_text() for text in spell_text_artists]
    for obj in list(spell_line_artists) + list(spell_text_artists):
        obj.set_picker(5)
    ax.add_artist(level_leg)
    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}

    selected_level_idx = None
    selected_spell_idx = None

    def _highlight_level(idx: int | None):
        nonlocal selected_level_idx
        selected_level_idx = idx
        for i, (line_artist, text_artist) in enumerate(zip(level_lines_artists, level_text_artists)):
            active = idx is not None and i == idx
            line_artist.set_linewidth(3 if active else 2)
            base = level_base_labels[i]
            text_artist.set_text(_underline_text(base) if active else base)
            text_artist.set_fontweight("bold" if active else "normal")
            text_artist.set_color("#000000")

    def _highlight_spell(idx: int | None):
        nonlocal selected_spell_idx
        selected_spell_idx = idx
        for i, (line_artist, text_artist) in enumerate(zip(spell_line_artists, spell_text_artists)):
            active = idx is not None and i == idx
            line_artist.set_linewidth(3 if active else 2)
            base = spell_base_labels[i]
            text_artist.set_text(_underline_text(base) if active else base)
            text_artist.set_fontweight("bold" if active else "normal")
            text_artist.set_color("#000000")

    def on_pick_level(event):
        if event.artist not in level_lines_artists and event.artist not in level_text_artists:
            return
        if event.artist in level_lines_artists:
            idx = level_lines_artists.index(event.artist)
        else:
            idx = level_text_artists.index(event.artist)
        _highlight_spell(None)
        lvl_clicked = union_levels[idx]
        curr_state = all(line.get_alpha() == 1.0 for line in level_lines[lvl_clicked])
        if curr_state and all(
            other.get_alpha() < 0.5 for lvl, lines in level_lines.items() if lvl != lvl_clicked for other in lines
        ):
            for line in plots:
                line.set_alpha(original_alphas[line])
            _highlight_level(None)
        else:
            for lvl, lines in level_lines.items():
                for line in lines:
                    line.set_alpha(1.0 if lvl == lvl_clicked else 0.2)
            _highlight_level(idx)
        fig.canvas.draw_idle()

    def on_pick_spell(event):
        if event.artist not in spell_line_artists and event.artist not in spell_text_artists:
            return
        if event.artist in spell_line_artists:
            idx = spell_line_artists.index(event.artist)
        else:
            idx = spell_text_artists.index(event.artist)
        _highlight_level(None)
        sel_lines = spell_lines.get(idx, [])
        if sel_lines and all(line.get_alpha() == 1.0 for line in sel_lines) and all(
            line.get_alpha() < 0.5 for line in plots if line not in sel_lines
        ):
            for line in plots:
                line.set_alpha(original_alphas[line])
            _highlight_spell(None)
        else:
            for j, lines in spell_lines.items():
                for line in lines:
                    line.set_alpha(1.0 if j == idx else 0.2)
            _highlight_spell(idx)
        fig.canvas.draw_idle()

    def on_pick(event):
        if event.artist in level_lines_artists or event.artist in level_text_artists:
            on_pick_level(event)
        elif event.artist in spell_line_artists or event.artist in spell_text_artists:
            on_pick_spell(event)

    fig.canvas.mpl_connect("pick_event", on_pick)
    # Store reference to prevent garbage collection
    annotator = InteractiveAnnotator(
        ax,
        fig,
        line_data,
        value_name="Value",
        all_points=all_points,
        line_labels=line_labels,
    )
    persistent = getattr(fig.canvas, "_persistent_callbacks", [])
    persistent.append(annotator)
    setattr(fig.canvas, "_persistent_callbacks", persistent)
    if not plots:
        plt.close(fig)
        raise ValueError("No overlapping damage distributions to compare for the selected spells.")
    return fig
