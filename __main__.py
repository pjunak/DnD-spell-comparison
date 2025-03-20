"""
Created by Petr Junák
"""

import random
import matplotlib.pyplot as plt
import math
import numpy as np
from magic import spells as spells_data
from magic import cantrips as cantrips_data
import calculations

settings = {"modifier": 0}

def ordinal(n):
    return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= n % 100 < 20 else n % 10, "th")

def list_spells(spell_type=None):
    all_spells = {}
    mods = [spells_data, cantrips_data] if spell_type is None else ([spells_data] if spell_type == "spell" else [cantrips_data])
    for mod in mods:
        for k, v in mod.__dict__.items():
            if not k.startswith('__') and isinstance(v, dict):
                all_spells[k] = v
    sorted_spells = sorted(all_spells.items(), key=lambda x: x[1].get("name", x[0]).lower())
    for idx, (key, data) in enumerate(sorted_spells, start=1):
        print(f"{idx}. {data.get('name', key)}")
    return {str(i): (key, data) for i, (key, data) in enumerate(sorted_spells, start=1)}

def change_modifier():
    while True:
        new_mod = input("Enter new spellcasting modifier (integer) (B to go back, X to exit): ").strip().lower()
        if new_mod == "b":
            return
        if new_mod == "x":
            exit("Exiting...")
        try:
            settings["modifier"] = int(new_mod)
            print(f"Modifier changed to {settings['modifier']}.")
            return
        except ValueError:
            print("Invalid input.")

def main_loop():
    while True:
        print("\n--- Main Menu ---")
        print(f"Modifier: {settings['modifier']} (press M to change)")
        print("  S - Show a single spell")
        print("  C - Compare spells/cantrips")
        print("  X - Exit")
        action = input("Choice: ").strip().lower()
        if action == "x":
            break
        if action == "m":
            change_modifier()
            continue
        if action == "s":
            spells_dict = list_spells()
            choice = input("Select a spell by number (B to go back, X to exit): ").strip().lower()
            if choice in ["x", "b"]:
                if choice == "x":
                    break
                continue
            if choice not in spells_dict:
                choice = "1"
            spell_key, params = spells_dict[choice]
            spell_full_name = params.get("name", spell_key)
            print(f"You selected: {spell_full_name}")
            base_level = params.get("base_level", 1)
            if base_level == 0:
                print(f"{spell_full_name} (cantrip) will be plotted for effective levels 1-4.")
            else:
                print(f"{spell_full_name} will be plotted for spell levels {base_level}-9.")
            mod = settings["modifier"]
            valueName = params.get("valueName", "Value")
            from plotting import plot_spell
            plot_spell(params, mod, spell_full_name, valueName)
        elif action == "c":
            print("Compare which type? (S)pells or (C)antrips?")
            type_choice = input("Choice (S/C): ").strip().lower()
            if type_choice not in ["s", "c"]:
                print("Invalid selection.")
                continue
            spell_type = "spell" if type_choice == "s" else "cantrip"
            spells_dict = list_spells(spell_type)
            print("Enter spells to compare separated by spaces (e.g., '1 3') (B to go back, X to exit):")
            selection = input("Spell numbers: ").strip().lower()
            if selection in ["x", "b"]:
                if selection == "x":
                    break
                continue
            indices = selection.split()
            if len(indices) not in [2, 3]:
                print("Select exactly 2 or 3 spells for comparison.")
                continue
            selected_spells = []
            for idx in indices:
                if idx in spells_dict:
                    selected_spells.append(spells_dict[idx])
                else:
                    print(f"Spell number {idx} is invalid.")
            if not selected_spells:
                continue
            mod = settings["modifier"]
            from plotting import compare_spells
            compare_spells(selected_spells, mod)
        else:
            print("Invalid action. Choose S, C, M or X.")

if __name__ == "__main__":
    main_loop()