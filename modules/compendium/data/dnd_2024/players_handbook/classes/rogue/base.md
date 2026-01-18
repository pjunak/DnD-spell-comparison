---
name: Rogue
type: class
hit_die: d8
primary_ability:
- DEX
saves:
- DEX
- INT
proficiencies:
  armor:
  - light
  weapons:
  - simple
  - martial (finesse)
  tools:
  - Thieves' Tools
  skills_choose: 4
  skill_list:
  - Acrobatics
  - Athletics
  - Deception
  - Insight
  - Intimidation
  - Investigation
  - Perception
  - Persuasion
  - Sleight of Hand
  - Stealth
spellcasting: null
progression:
- level: 1
  features:
  - Expertise
  - Sneak Attack
  - Thieves' Cant
  - Weapon Mastery
  options:
  - key: rogue_expertise_1_1
    type: expertise
    label: "Expertise (1st skill)"
    choices: any_proficient_skill
  - key: rogue_expertise_1_2
    type: expertise
    label: "Expertise (2nd skill)"
    choices: any_proficient_skill
- level: 2
  features:
  - Cunning Action
- level: 3
  features:
  - Rogue Subclass
  - Steady Aim
- level: 4
  features:
  - Ability Score Improvement
- level: 5
  features:
  - Cunning Strike
  - Uncanny Dodge
- level: 6
  features:
  - Expertise
  options:
  - key: rogue_expertise_6_1
    type: expertise
    label: "Expertise (3rd skill)"
    choices: any_proficient_skill
  - key: rogue_expertise_6_2
    type: expertise
    label: "Expertise (4th skill)"
    choices: any_proficient_skill
- level: 7
  features:
  - Evasion
  - Reliable Talent
- level: 8
  features:
  - Ability Score Improvement
- level: 9
  features:
  - Subclass Feature
- level: 10
  features:
  - Ability Score Improvement
- level: 11
  features:
  - Improved Cunning Strike
- level: 12
  features:
  - Ability Score Improvement
- level: 13
  features:
  - Subclass Feature
- level: 14
  features:
  - Devious Strikes
- level: 15
  features:
  - Slippery Mind
- level: 16
  features:
  - Ability Score Improvement
- level: 17
  features:
  - Subclass Feature
- level: 18
  features:
  - Elusive
- level: 19
  features:
  - Epic Boon
- level: 20
  features:
  - Stroke of Luck
id: class:rogue
---

Rogues rely on skill, stealth, and their foes' vulnerabilities to get the upper hand in any situation. They have a knack for finding the solution to just about any problem, demonstrating a resourcefulness and versatility that is the cornerstone of any successful adventuring party.

### Level 1: Expertise

You gain Expertise in two of your Skill Proficiencies of your choice.

### Level 1: Sneak Attack

You know how to strike subtly and exploit a foe's distraction. Once per turn, you can deal an extra 1d6 damage to one creature you hit with an Attack Roll if you have Advantage on the roll and the attack uses a Finesse or a Ranged weapon.

You don't need Advantage on the Attack Roll if at least one of your allies is within 5 feet of the target, the ally isn't Incapacitated, and you don't have Disadvantage on the Attack Roll.

The amount of the extra damage increases as you gain levels in this class, as shown in the Sneak Attack column of the Rogue Features table.

### Level 1: Thieves' Cant

You have learned Thieves' Cant, a secret mix of dialect, jargon, and code that allows you to hide messages in seemingly normal conversation. You also gain proficiency with the Thieves' Tools.

### Level 1: Weapon Mastery

Your training with weapons allows you to use the mastery properties of two kinds of weapons of your choice with which you have proficiency, such as Daggers and Shortbows. Whenever you finish a Long Rest, you can practice weapon drills and change one of those weapon choices.

### Level 2: Cunning Action

Your quick thinking and agility allow you to move and act quickly. You can take a Bonus Action on each of your turns in Combat. This action can be used only to take the Dash, Disengage, or Hide action.

### Level 3: Rogue Subclass

You choose an archetype that you strive to emulate, such as the Arcane Trickster, Assassin, Soulknife, or Thief. The archetype you choose grants you features at Level 3 and again at Levels 9, 13, and 17.

### Level 3: Steady Aim

As a Bonus Action, you give yourself Advantage on your next Attack Roll on the current turn. You can use this Bonus Action only if you haven't moved during this turn, and after you use the Bonus Action, your Speed is 0 until the end of the current turn.

### Level 5: Cunning Strike

You have developed a way to make your Sneak Attack even more debilitating. When you deal Sneak Attack damage, you can trade one of the Sneak Attack dice to apply one of the following effects.

**Disarm.** The target must succeed on a Dexterity saving throw or drop one item of your choice that it's holding.
**Poison.** The target must succeed on a Constitution saving throw or be Poisoned for 1 minute.
**Trip.** The target must succeed on a Dexterity saving throw or be knocked Prone.
**Withdraw.** After you attack, you can move up to half your Speed without provoking Opportunity Attacks.

### Level 5: Uncanny Dodge

When an attacker that you can see hits you with an Attack, you can use your Reaction to halve the attack's damage against you.

### Level 7: Evasion

You can nimbly dodge out of the way of certain area effects, such as a red dragon's fiery breath or an *Ice Storm* spell. When you are subjected to an Effect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage if you succeed on the saving throw, and only half damage if you fail.

### Level 7: Reliable Talent

Whenever you make an Ability Check that uses one of your Skill or Tool Proficiencies, you can treat a d20 roll of 9 or lower as a 10.

### Level 11: Improved Cunning Strike

You can use up to two Cunning Strike effects when you deal Sneak Attack damage, paying the die cost for each.

### Level 14: Devious Strikes

You have practiced new ways to effectively daze and disable your enemies. The following effects are now among your Cunning Strike options.

**Daze (Cost: 2 Dice).** The target must succeed on a Constitution saving throw or be Dazed for 1 minute.
**Knock Out (Cost: 6 Dice).** The target must succeed on a Constitution saving throw or fall Unconscious for 1 minute or until it takes damage.

### Level 15: Slippery Mind

You have acquired greater mental strength. You gain Proficiency in Wisdom and Charisma Saving Throws.

### Level 18: Elusive

You are so evasive that attackers rarely gain the upper hand against you. No Attack Roll has Advantage against you while you aren't Incapacitated.

### Level 19: Epic Boon

You gain an Epic Boon feat or another feat of your choice for which you qualify. Boon of the Night Spirit is recommended.

### Level 20: Stroke of Luck

You have an uncanny knack for succeeding when you need to. If you fail a d20 Test, you can turn the roll into a 20.

Once you use this feature, you can't use it again until you finish a Short or Long Rest.
