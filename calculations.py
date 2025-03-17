import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import dices

def diceSelector(dice_value):
    """
    Return a list representing a dice with faces 1 to dice_value.
    For example, diceSelector(6) returns [1, 2, 3, 4, 5, 6].
    """
    return list(range(1, dice_value + 1))

def chain_spell_distribution(start_rolls, add_rolls, initial_dice_value, additional_dice_value,
                             modifier=0, levels=1, constant_per_die=0):
    """
    Compute the probability distribution for a spell.
    If constant_per_die is provided, each die outcome is increased by that constant.
    """
    # Adjust dice: add constant_per_die to each face.
    dice_initial = [face + constant_per_die for face in diceSelector(initial_dice_value)]
    distribution = dices.combination_distribution(dice_initial, start_rolls, modifier)
    
    dice_add = [face + constant_per_die for face in diceSelector(additional_dice_value)]
    for _ in range(levels - 1):
        new_distribution = {}
        sub_dist = dices.combination_distribution(dice_add, add_rolls, 0)
        for current_sum, prob in distribution.items():
            for add_sum, add_prob in sub_dist.items():
                total = current_sum + add_sum
                new_distribution[total] = new_distribution.get(total, 0) + prob * add_prob
        distribution = new_distribution
    
    total = sum(distribution.values())
    if total:
        distribution = {k: v / total for k, v in distribution.items()}
    
    return distribution

def showGraph(levels, modifier, valueLabel="Value", spell_full_name="Spell"):
    """
    Plot the probability distributions for different spell levels.
    The graph title is displayed in the format:
      "<Spell Full Name> <Damage/Healing> by levels with +<modifier> modifier"
    """
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mtick

    title = f"{spell_full_name} {valueLabel} by levels with +{modifier} modifier"
    fig, ax = plt.subplots()
    fig.suptitle(title)
    ax.set_xlabel(valueLabel)
    ax.set_ylabel("Probability")
    
    # Store each line's data and create a master list of all points.
    line_data = {}   # {line: (x_vals, y_vals)}
    all_points = []  # list of tuples: (line, x, y)
    
    plots = []
    for lvl, dist in sorted(levels.items()):
        x_vals, y_vals = zip(*sorted(dist.items()))
        line, = ax.plot(x_vals, y_vals, label=f"Level {lvl}", marker='o')
        line_data[line] = (x_vals, y_vals)
        plots.append(line)
        for x, y in zip(x_vals, y_vals):
            all_points.append((line, x, y))
    
    # Set y-axis ticks to display percent with one decimal point.
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=1))
    
    leg = ax.legend(title="Spell Level", loc="upper right", fancybox=True, shadow=True)
    
    # Enable picking on the legend lines and store mapping between legend and plot lines.
    legend_lines = leg.get_lines()
    for legline in legend_lines:
        legline.set_picker(5)  # 5 pts tolerance
    
    # Store the original alphas.
    original_alphas = {line: line.get_alpha() if line.get_alpha() is not None else 1.0 for line in plots}
    
    # Define the pick event.
    def on_pick(event):
        # Check if a legend line was picked.
        if event.artist in legend_lines:
            idx = legend_lines.index(event.artist)
            clicked_line = plots[idx]
            # Determine if this line is already "active" (others hidden/faded).
            if clicked_line.get_alpha() == 1.0 and all(
                    other.get_alpha() < 1.0 for i, other in enumerate(plots) if i != idx):
                # Reset all lines to full opacity.
                for line in plots:
                    line.set_alpha(original_alphas[line])
            else:
                # Set clicked line to full opacity and fade others.
                for i, line in enumerate(plots):
                    if i == idx:
                        line.set_alpha(1.0)
                    else:
                        line.set_alpha(0.2)
            fig.canvas.draw_idle()
    
    fig.canvas.mpl_connect("pick_event", on_pick)
    
    # Create a single annotation that will update on mouse movement.
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
        
        # Find the nearest point using Euclidean distance.
        nearest_point = None
        min_dist = float("inf")
        for (line, x, y) in all_points:
            dist = ((event.xdata - x)**2 + (event.ydata - y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                nearest_point = (line, x, y)
        
        if nearest_point is None:
            return
        
        line, x_val, y_val = nearest_point
        
        # Get cumulative probabilities for the chosen line.
        x_vals, y_vals_line = line_data[line]
        p_greater = sum(prob for val, prob in zip(x_vals, y_vals_line) if val > x_val)
        p_less = sum(prob for val, prob in zip(x_vals, y_vals_line) if val < x_val)
        x_disp = round(x_val * 2) / 2.0  # Round to nearest 0.5
        
        annot.xy = (x_val, y_val)
        text = (f"{valueLabel}: {x_disp:.1f}\n"
                f"Probability: {y_val:.1%}\n"
                f"P(> {valueLabel}): {p_greater:.1%}\n"
                f"P(< {valueLabel}): {p_less:.1%}")
        annot.set_text(text)
        annot.get_bbox_patch().set_facecolor("lightyellow")
        annot.set_visible(True)
        fig.canvas.draw_idle()
    
    fig.canvas.mpl_connect("motion_notify_event", update_annotation)
    plt.show()