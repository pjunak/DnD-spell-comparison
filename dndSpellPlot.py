"""
    Created by Petr Junák
    junak.online
    junakpetr@gmail.com
"""

#Imports
import random
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import math
import numpy as np



#Defined default values and dices
MODIFIER = 3
D4 = [1,2,3,4]
D6 = [1,2,3,4,5,6]
D8 = [1,2,3,4,5,6,7,8]
D10 = [1,2,3,4,5,6,7,8,9,10]
D12 = [1,2,3,4,5,6,7,8,9,10,11,12]
D20 = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

#Dice throw symulation
def d6Rand(x):
    result = 0
    for i in range (x):
        result += random.randint(1,6)
    return result

#Spell rolls combinations
def cureWounds(lvl):
    rollSet = {(roll + MODIFIER):1 for roll in D8}
    for i in range(1, lvl):
        newRollSet = {}
        for key in rollSet.copy():
            for roll in D8:
                if (key + roll) in newRollSet:
                    newRollSet[key+roll] += rollSet[key]
                else:
                    newRollSet[key+roll] = 1
        rollSet = newRollSet

    for key in rollSet.keys():
        rollSet[key] = rollSet[key] / 8**lvl
        
    return rollSet


levels = {}

for lvl in range (1,10):
    values = {}
    values = cureWounds(lvl)
    levels.update({lvl:values})


fig, ax = plt.subplots()
fig.suptitle(f"Probability of Healing Touch value by levels with +{MODIFIER} modifier")
fig.supxlabel("X = sum of rolls + modifier")
fig.supylabel("Y = chance of occurance")

for lvl in range (0,9):
    x, y = zip(*levels[lvl+1].items())
    ax.plot(x, y, label=lvl+1)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax = 1, decimals=1, symbol = '%', is_latex = False))
    ax.legend(title='Spell levels')



plt.show()