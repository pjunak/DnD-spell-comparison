import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import calculations

LEVEL_DEFAULT = 9

def extract_effect_params(spell):
    effects = spell.get("effects", [])
    primary = None
    for eff in effects:
        if eff.get("effect_type", "")=="primary":
            primary = eff
            break
    if primary is None and effects:
        primary = effects[0]
    damage = primary.get("effect_data", {}).get("damage", {}) if primary else {}
    start_rolls = damage.get("base", {}).get("dice", 1)
    initial_die = damage.get("base", {}).get("die", 6)
    add_rolls = damage.get("scaling", {}).get("dice_per_slot", 0)
    additional_die = damage.get("scaling", {}).get("die", 6)
    use_modifier = damage.get("use_modifier", False)
    constant = damage.get("constant", 0)
    valueName = damage.get("type", "Damage").capitalize()
    return {
        "start_rolls": start_rolls,
        "initial_dice_value": initial_die,
        "add_rolls": add_rolls,
        "additional_dice_value": additional_die,
        "use_modifier": use_modifier,
        "constant_per_die": constant,
        "valueName": valueName
    }

def plot_spell(spell, mod, spell_full_name):
    params = extract_effect_params(spell)
    lvl = spell.get("level", 1)
    level_range = list(range(1,5)) if lvl==0 else list(range(lvl, LEVEL_DEFAULT+1))
    level_distributions = {}
    for level in level_range:
        lvl_param = level if lvl==0 else (level - lvl + 1)
        distribution = calculations.chain_spell_distribution(
            start_rolls=params["start_rolls"],
            add_rolls=params["add_rolls"],
            initial_dice_value=params["initial_dice_value"],
            additional_dice_value=params["additional_dice_value"],
            modifier=mod,
            levels=lvl_param,
            constant_per_die=params["constant_per_die"]
        )
        level_distributions[level] = distribution
    title = f"{spell_full_name} {params['valueName']} by levels with +{mod} modifier"
    fig, ax = plt.subplots()
    fig.suptitle(title)
    ax.set_xlabel(params["valueName"])
    ax.set_ylabel("Probability")
    plt.text(0.5, 1.02, "Click to isolate", transform=ax.transAxes, ha="center", fontsize=10, color="gray")
    line_data = {}
    all_points = []
    plots = []
    for level, dist in sorted(level_distributions.items()):
        sp = sorted([(x,y) for x,y in dist.items() if y>0], key=lambda p: p[0])
        if not sp:
            continue
        x_vals, y_vals = zip(*sp)
        line, = ax.plot(x_vals, y_vals, label=f"Level {level}", marker='o')
        plots.append(line)
        line_data[line] = (x_vals, y_vals)
        for x,y in zip(x_vals, y_vals):
            all_points.append((line,x,y))
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
    for obj in legend_objs + leg.get_texts()[:-1]:
        obj.set_picker(5)
    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}
    def on_pick(event):
        if event.artist in legend_objs:
            idx = legend_objs.index(event.artist)
        elif event.artist in leg.get_texts()[:-1]:
            idx = leg.get_texts()[:-1].index(event.artist)
        else:
            return
        clicked_line = plots[idx]
        if clicked_line.get_alpha()==1.0 and all(other.get_alpha()<1.0 for i,other in enumerate(plots) if i!=idx):
            for line in plots:
                line.set_alpha(original_alphas[line])
        else:
            for i, line in enumerate(plots):
                line.set_alpha(1.0 if i==idx else 0.1)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("pick_event", on_pick)
    annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)
    def update_annotation(event):
        if event.inaxes!=ax or event.xdata is None or event.ydata is None:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return
        nearest_point = None
        min_dist = float("inf")
        for (line,x,y) in all_points:
            d = ((event.xdata-x)**2+(event.ydata-y)**2)**0.5
            if d < min_dist:
                min_dist = d
                nearest_point = (line,x,y)
        if nearest_point is None:
            return
        line, x_val, y_val = nearest_point
        x_vals, y_vals_line = line_data[line]
        p_greater = sum(prob for val,prob in zip(x_vals,y_vals_line) if val>x_val)
        p_less = sum(prob for val,prob in zip(x_vals,y_vals_line) if val<x_val)
        x_disp = round(x_val)
        annot.xy = (x_val,y_val)
        text = (f"{params['valueName']}: {x_disp:.0f}\n"
                f"Probability: {y_val:.3%}\n"
                f"P(> {params['valueName']}): {p_greater:.3%}\n"
                f"P(< {params['valueName']}): {p_less:.3%}")
        annot.set_text(text)
        annot.get_bbox_patch().set_facecolor("lightyellow")
        annot.set_visible(True)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", update_annotation)
    return fig

def compare_spells(selected_spells, mod):
    from matplotlib.lines import Line2D
    is_cantrip = [s.get("level", 1)==0 for s in selected_spells]
    if not (all(is_cantrip) or (not any(is_cantrip))):
        print("Error: Cannot compare spells with cantrips.")
        return
    if len(selected_spells) not in [2,3]:
        print("Error: Select exactly 2 or 3 spells to compare.")
        return
    spell_levels = []
    for s in selected_spells:
        if s.get("level",1)==0:
            available = set(range(1,5))
        else:
            base = s.get("level", 1)
            available = set(range(base,10))
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
    colors = {lvl: cmap((lvl-min_lvl)/(max_lvl-min_lvl+1)) for lvl in union_levels}
    fig, ax = plt.subplots()
    header_names = [s.get("name","Unknown") for s in selected_spells]
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
        for j, s in enumerate(selected_spells):
            if s.get("level",1)==0:
                if lvl not in range(1,5):
                    continue
                lvl_param = lvl
            else:
                base = s.get("level",1)
                if lvl < base:
                    continue
                lvl_param = lvl - base + 1
            params = extract_effect_params(s)
            distribution = calculations.chain_spell_distribution(
                start_rolls=params["start_rolls"],
                add_rolls=params["add_rolls"],
                initial_dice_value=params["initial_dice_value"],
                additional_dice_value=params["additional_dice_value"],
                modifier=mod,
                levels=lvl_param,
                constant_per_die=params["constant_per_die"]
            )
            filtered = sorted([(x,y) for x,y in distribution.items() if y>0], key=lambda p: p[0])
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
            for x,y in zip(x_vals, y_vals):
                all_points.append((line,x,y))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=1))
    level_handles = []
    level_labels = []
    for lvl in union_levels:
        if is_cantrip[0]:
            mapping = {1:"<5",2:"5",3:"11",4:"17"}
            label = f"Player Level {mapping.get(lvl,lvl)}"
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
    for i, s in enumerate(selected_spells):
        s_style = styles[i % len(styles)]
        handle = Line2D([], [], linestyle=s_style["linestyle"], marker=s_style["marker"], color="black", lw=2)
        spell_handles.append(handle)
        spell_labels.append(s.get("name", "Unknown"))
    spell_leg = ax.legend(spell_handles, spell_labels, title="Spells", loc="upper left", fancybox=True, shadow=True)
    for obj in spell_leg.get_lines() + spell_leg.get_texts():
        obj.set_picker(5)
    ax.add_artist(level_leg)
    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}
    def on_pick_level(event):
        if event.artist not in level_interactive and event.artist not in level_leg.get_texts()[:-1]:
            return
        if event.artist in level_interactive:
            idx = level_interactive.index(event.artist)
        else:
            idx = level_leg.get_texts()[:-1].index(event.artist)
        sorted_lvls = sorted(level_lines.keys())
        lvl_clicked = sorted_lvls[idx]
        curr_state = all(line.get_alpha()==1.0 for line in level_lines[lvl_clicked])
        if curr_state and all(other.get_alpha()<0.5 for lvl, lines in level_lines.items() if lvl!=lvl_clicked for other in lines):
            for line in plots:
                line.set_alpha(original_alphas[line])
        else:
            for lvl, lines in level_lines.items():
                for line in lines:
                    line.set_alpha(1.0 if lvl==lvl_clicked else 0.2)
        fig.canvas.draw_idle()
    def on_pick_spell(event):
        spell_objs = spell_leg.get_lines() + spell_leg.get_texts()
        if event.artist not in spell_objs:
            return
        if event.artist in spell_leg.get_lines():
            idx = spell_leg.get_lines().index(event.artist)
        else:
            idx = spell_leg.get_texts().index(event.artist)
        sel_lines = spell_lines.get(idx, [])
        if sel_lines and all(line.get_alpha()==1.0 for line in sel_lines) and \
           all(line.get_alpha()<0.5 for line in plots if line not in sel_lines):
            for line in plots:
                line.set_alpha(original_alphas[line])
        else:
            for j, lines in spell_lines.items():
                for line in lines:
                    line.set_alpha(1.0 if j==idx else 0.2)
        fig.canvas.draw_idle()
    def on_pick(event):
        if event.artist in level_interactive or event.artist in level_leg.get_texts()[:-1]:
            on_pick_level(event)
        elif event.artist in spell_leg.get_lines() or event.artist in spell_leg.get_texts():
            on_pick_spell(event)
    fig.canvas.mpl_connect("pick_event", on_pick)
    annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)
    def update_annotation(event):
        if event.inaxes!=ax or event.xdata is None or event.ydata is None:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
            return
        nearest_point = None
        min_dist = float("inf")
        for (line,x,y) in all_points:
            d = ((event.xdata-x)**2+(event.ydata-y)**2)**0.5
            if d < min_dist:
                min_dist = d
                nearest_point = (line,x,y)
        if nearest_point is None:
            return
        line, x_val, y_val = nearest_point
        x_vals, y_vals_line = line_data[line]
        p_greater = sum(prob for val,prob in zip(x_vals,y_vals_line) if val>x_val)
        p_less = sum(prob for val,prob in zip(x_vals,y_vals_line) if val<x_val)
        x_disp = round(x_val)
        annot.xy = (x_val,y_val)
        text = (f"Value: {x_disp}\n"
                f"Probability: {y_val:.3%}\n"
                f"P(> {x_disp}): {p_greater:.3%}\n"
                f"P(< {x_disp}): {p_less:.3%}")
        annot.set_text(text)
        annot.get_bbox_patch().set_facecolor("lightyellow")
        annot.set_visible(True)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", update_annotation)
    return fig
