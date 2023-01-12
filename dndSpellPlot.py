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
import rules
import spellList

#Function for ordinals. Expects a number and returns correct ordinal.
def ordinal(n):
  return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= n % 100 < 20 else n % 10, "th")

#Default values
MODIFIER = 5
INDICE = rules.D8
INNUM = 1
ADDDICE = INDICE
ADDNUM = 1
LEVEL = 9


#Dice throw symulation
def d6Rand(x):
    result = 0
    for i in range (x):
        result += random.randint(1,6)
    return result

#Spell rolls combinations for given spel level
def cureWounds(lvl):
    rollSet = {(roll + MODIFIER):1 for roll in rules.D8}
    for i in range(1, lvl):
        newRollSet = {}
        for key in rollSet.copy():
            for roll in rules.D8:
                if (key + roll) in newRollSet:
                    newRollSet[key+roll] += rollSet[key]
                else:
                    newRollSet[key+roll] = 1
        rollSet = newRollSet

    for key in rollSet.keys():
        rollSet[key] = rollSet[key] / 8**lvl
        
    return rollSet


def firstRollSet(lvl,dice,num,mod):
    rollSet = {(roll + mod):lvl for roll in dice}
    newRollSet = {}
    for n in range(1,num):
        for key in rollSet.copy():
            for roll in dice:
                if (key + roll) in newRollSet:
                    newRollSet[key+roll] += rollSet[key]
                else:
                    newRollSet[key+roll] = 1
        rollSet = newRollSet
        print(num)
    return rollSet

    #Spell rolls combinations
def spell( inLvl, inDice, inNum, addDice, addNum, lvl, mod):
    dice = rules.diceSelector(inDice)
    rollSet = firstRollSet(inLvl, dice, inNum, mod)

    for i in range(inLvl, lvl):
        for n in range(addNum):
            newRollSet = {}
            for key in rollSet.copy():
                for roll in dice:
                    if (key + roll) in newRollSet:
                        newRollSet[key+roll] += rollSet[key]
                    else:
                        newRollSet[key+roll] = 1
            rollSet = newRollSet

    for key in rollSet.keys():
        rollSet[key] = rollSet[key] / ((inDice**inNum)*(addDice**addNum)**(lvl-inLvl))
        
    return rollSet


def showGraph(levels):
    fig, ax = plt.subplots()
    fig.suptitle(f"Probability of Healing Touch value by levels with +{MODIFIER} modifier")
    fig.supxlabel("X = sum of rolls + modifier")
    fig.supylabel("Y = chance of occurance")


    for lvl in range (0,len(levels)):
        x, y = zip(*levels[lvl+1].items())
        ax.plot(x, y, label=ordinal(lvl+1))
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax = 1, decimals=1, symbol = '%', is_latex = False))
        ax.legend(title='Spell level')

    plt.show()


level = int(input("Insert spell level: ")) 
level if level in range(10) else LEVEL

mod = int(input("Insert spell modificator: ")) 
mod if mod in range(-20,20) else MODIFIER

levels = {}

for lvl in range (1,(level+1)):
    values = {}
    #values = cureWounds(lvl)
    values = spell(*spellList.fireball,lvl,mod)
    levels.update({lvl:values})
showGraph(levels)
