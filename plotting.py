import random
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import math
import numpy as np
import calculations
from matplotlib.lines import Line2D

LEVEL_DEFAULT = 9

def plot_spell(params, mod, spell_full_name, valueLabel):
    base_level = params.get("base_level", 1)
    level_range = list(range(1, 5)) if base_level == 0 else list(range(base_level, LEVEL_DEFAULT + 1))
    level_distributions = {}
    for level in level_range:
        levels_param = level if base_level == 0 else (level - base_level + 1)
        distribution = calculations.chain_spell_distribution(
            start_rolls=params["start_rolls"],
            add_rolls=params["add_rolls"],
            initial_dice_value=params["initial_dice_value"],
            additional_dice_value=params["additional_dice_value"],
            modifier=mod,
            levels=levels_param,
            constant_per_die=params.get("constant_per_die", 0)
        )
        level_distributions[level] = distribution

    title = f"{spell_full_name} {valueLabel} by levels with +{mod} modifier"
    fig, ax = plt.subplots()
    fig.suptitle(title)
    ax.set_xlabel(valueLabel)
    ax.set_ylabel("Probability")
    plt.text(0.5, 1.02, "Click to isolate", transform=ax.transAxes,
             ha="center", fontsize=10, color="gray")

    line_data = {}
    all_points = []
    plots = []
    for lvl, dist in sorted(level_distributions.items()):
        sorted_points = sorted([(x, y) for x, y in dist.items() if y > 0], key=lambda pair: pair[0])
        if not sorted_points:
            continue
        x_vals, y_vals = zip(*sorted_points)
        line, = ax.plot(x_vals, y_vals, label=f"Level {lvl}", marker='o')
        plots.append(line)
        line_data[line] = (x_vals, y_vals)
        for x, y in zip(x_vals, y_vals):
            all_points.append((line, x, y))

    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=1))
    handles, labels = ax.get_legend_handles_labels()
    dummy = Line2D([], [], linestyle="", color="none")
    handles.append(dummy)
    labels.append("Click to isolate")
    leg = ax.legend(handles, labels, title="Spell Level", loc="upper right", fancybox=True, shadow=True)
    for obj in leg.get_lines()[:-1] + leg.get_texts()[:-1]:
        obj.set_picker(5)

    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}

    def on_pick(event):
        if event.artist in leg.get_lines()[:-1]:
            idx = leg.get_lines()[:-1].index(event.artist)
        elif event.artist in leg.get_texts()[:-1]:
            idx = leg.get_texts()[:-1].index(event.artist)
        else:
            return
        clicked_line = plots[idx]
        if clicked_line.get_alpha() == 1.0 and all(other.get_alpha() < 1.0 for i, other in enumerate(plots) if i != idx):
            for line in plots:
                line.set_alpha(original_alphas[line])
        else:
            for i, line in enumerate(plots):
                line.set_alpha(1.0 if i == idx else 0.2)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("pick_event", on_pick)

    annot = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_annotation(event):
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return
        nearest_point = None
        min_dist = float("inf")
        for (line, x, y) in all_points:
            effective_alpha = line.get_alpha() if line.get_alpha() is not None else 1.0
            if effective_alpha != 1.0:
                continue
            dist = ((event.xdata - x)**2 + (event.ydata - y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                nearest_point = (line, x, y)
        if nearest_point is None:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return
        line, x_val, y_val = nearest_point
        x_vals, y_vals_line = line_data[line]
        p_greater = sum(prob for val, prob in zip(x_vals, y_vals_line) if val > x_val)
        p_less = sum(prob for val, prob in zip(x_vals, y_vals_line) if val < x_val)
        x_disp = round(x_val)
        annot.xy = (x_val, y_val)
        text = (f"{valueLabel}: {x_disp}\n"
                f"Probability: {y_val:.3%}\n"
                f"P(> {x_disp}): {p_greater:.3%}\n"
                f"P(< {x_disp}): {p_less:.3%}")
        annot.set_text(text)
        annot.get_bbox_patch().set_facecolor("lightyellow")
        annot.set_visible(True)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", update_annotation)
    plt.show()

def compare_spells(selected_spells, mod):
    from calculations import chain_spell_distribution
    from matplotlib.lines import Line2D

    is_cantrip = [params.get("base_level", 1) == 0 for _, params in selected_spells]
    if not (all(is_cantrip) or (not any(is_cantrip))):
        print("Error: Cannot compare spells with cantrips.")
        return
    if len(selected_spells) not in [2, 3]:
        print("Error: Please select exactly 2 or 3 spells to compare.")
        return

    spell_levels = []
    for _, params in selected_spells:
        available = set(range(1, 5)) if params.get("base_level", 1) == 0 else set(range(params.get("base_level", 1), 10))
        spell_levels.append(available)
    union_levels = sorted(set().union(*spell_levels))
    if not union_levels:
        print("No common levels available.")
        return

    num_spells = len(selected_spells)
    styles = [
        {"linestyle": "-", "marker": "o"},
        {"linestyle": "--", "marker": "s"},
        {"linestyle": ":", "marker": "^"}
    ]
    cmap = plt.get_cmap("tab10")
    min_lvl, max_lvl = union_levels[0], union_levels[-1]
    colors = {lvl: cmap((lvl - min_lvl) / (max_lvl - min_lvl + 1)) for lvl in union_levels}

    fig, ax = plt.subplots()
    header_names = [params.get("name", key) for key, params in selected_spells]
    title = "Comparison: " + ", ".join(header_names) + f" with +{mod} modifier"
    fig.suptitle(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Probability")

    line_data = {}
    all_points = []
    plots = []
    level_lines = {lvl: [] for lvl in union_levels}
    spell_lines = {j: [] for j in range(num_spells)}

    for lvl in union_levels:
        for j, (spell_key, params) in enumerate(selected_spells):
            if params.get("base_level", 1) == 0:
                if lvl not in range(1, 5):
                    continue
                rel_level = lvl
            else:
                base = params.get("base_level", 1)
                if lvl < base:
                    continue
                rel_level = lvl - base + 1
            distribution = chain_spell_distribution(
                start_rolls=params["start_rolls"],
                add_rolls=params["add_rolls"],
                initial_dice_value=params["initial_dice_value"],
                additional_dice_value=params["additional_dice_value"],
                modifier=mod,
                levels=rel_level,
                constant_per_die=params.get("constant_per_die", 0)
            )
            filtered = sorted([(x, y) for x, y in distribution.items() if y > 0], key=lambda pair: pair[0])
            if not filtered:
                continue
            x_vals, y_vals = zip(*filtered)
            style = styles[j % len(styles)]
            line, = ax.plot(x_vals, y_vals, linestyle=style["linestyle"],
                            marker=style["marker"], color=colors[lvl])
            level_lines[lvl].append(line)
            spell_lines[j].append(line)
            plots.append(line)
            line_data[line] = (x_vals, y_vals)
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
        handle = Line2D([], [], color=colors[lvl], lw=2)
        level_handles.append(handle)
        level_labels.append(label)
    dummy1 = Line2D([], [], linestyle="", color="none")
    level_handles.append(dummy1)
    level_labels.append("Click to isolate level")
    level_leg = ax.legend(level_handles, level_labels, title="Level", loc="upper right", fancybox=True, shadow=True)
    level_interactive = level_leg.get_lines()[:-1]
    for obj in level_interactive + level_leg.get_texts()[:-1]:
        obj.set_picker(5)

    spell_handles = []
    spell_labels = []
    for i, (spell_key, params) in enumerate(selected_spells):
        s = styles[i % len(styles)]
        handle = Line2D([], [], linestyle=s["linestyle"], marker=s["marker"], color="black", lw=2)
        spell_handles.append(handle)
        spell_labels.append(params.get("name", spell_key))
    spell_leg = ax.legend(spell_handles, spell_labels, title="Spells", loc="upper left", fancybox=True, shadow=True)
    for obj in spell_leg.get_lines() + spell_leg.get_texts():
        obj.set_picker(5)
    ax.add_artist(level_leg)

    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}

    def on_pick_level(event):
        if event.artist not in level_interactive and event.artist not in level_leg.get_texts()[:-1]:
            return
        idx = level_interactive.index(event.artist) if event.artist in level_interactive else level_leg.get_texts()[:-1].index(event.artist)
        sorted_lvls = sorted(level_lines.keys())
        level_clicked = sorted_lvls[idx]
        curr_state = all(line.get_alpha() == 1.0 for line in level_lines[level_clicked])
        if curr_state and all(other.get_alpha() < 0.5 for lvl, lines in level_lines.items() if lvl != level_clicked for other in lines):
            for line in plots:
                line.set_alpha(original_alphas[line])
        else:
            for lvl, lines in level_lines.items():
                for line in lines:
                    line.set_alpha(1.0 if lvl == level_clicked else 0.1)
        fig.canvas.draw_idle()

    def on_pick_spell(event):
        spell_objs = spell_leg.get_lines() + spell_leg.get_texts()
        if event.artist not in spell_objs:
            return
        idx = spell_leg.get_lines().index(event.artist) if event.artist in spell_leg.get_lines() else spell_leg.get_texts().index(event.artist)
        selected_lines = spell_lines.get(idx, [])
        if selected_lines and all(line.get_alpha() == 1.0 for line in selected_lines) and \
           all(line.get_alpha() < 0.5 for line in plots if line not in selected_lines):
            for line in plots:
                line.set_alpha(original_alphas[line])
        else:
            for j, lines in spell_lines.items():
                for line in lines:
                    line.set_alpha(1.0 if j == idx else 0.1)
        fig.canvas.draw_idle()

    def on_pick(event):
        if event.artist in level_interactive or event.artist in level_leg.get_texts()[:-1]:
            on_pick_level(event)
        elif event.artist in spell_leg.get_lines() or event.artist in spell_leg.get_texts():
            on_pick_spell(event)
    fig.canvas.mpl_connect("pick_event", on_pick)

    annot = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_annotation(event):
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return
        nearest_point = None
        min_dist = float("inf")
        for (line, x, y) in all_points:
            effective_alpha = line.get_alpha() if line.get_alpha() is not None else 1.0
            if effective_alpha != 1.0:
                continue
            dist = ((event.xdata - x)**2 + (event.ydata - y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                nearest_point = (line, x, y)
        if nearest_point is None:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return
        line, x_val, y_val = nearest_point
        x_vals, y_vals_line = line_data[line]
        p_greater = sum(prob for val, prob in zip(x_vals, y_vals_line) if val > x_val)
        p_less = sum(prob for val, prob in zip(x_vals, y_vals_line) if val < x_val)
        x_disp = round(x_val)
        annot.xy = (x_val, y_val)
        text = (f"Value: {x_disp}\n"
                f"Probability: {y_val:.3%}\n"
                f"P(> {x_disp}): {p_greater:.3%}\n"
                f"P(< {x_disp}): {p_less:.3%}")
        annot.set_text(text)
        annot.get_bbox_patch().set_facecolor("lightyellow")
        annot.set_visible(True)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", update_annotation)
    plt.show()
