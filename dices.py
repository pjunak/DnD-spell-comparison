def combination_distribution(dice, rolls, modifier=0):
    """
    Calculate the distribution of all possible sums when rolling the given dice.
    'dice' is a list of faces, 'rolls' is the number of dice to roll,
    and 'modifier' is added to each outcome.
    Returns a dict mapping sum -> probability.
    """
    # Start with the distribution for one roll.
    dist = {}
    for outcome in dice:
        total = outcome + modifier
        dist[total] = dist.get(total, 0) + 1
    # Convolve the distribution for remaining rolls.
    for _ in range(rolls - 1):
        new_dist = {}
        for current_sum, count in dist.items():
            for outcome in dice:
                new_total = current_sum + outcome
                new_dist[new_total] = new_dist.get(new_total, 0) + count
        dist = new_dist
    total_outcomes = len(dice) ** rolls
    for k in dist:
        dist[k] /= total_outcomes
    return dist