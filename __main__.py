"""
Created by Petr Junák
"""

import random
import matplotlib.pyplot as plt
import math
import numpy as np
import db
import calculations

settings = {"modifier": 0}

def ordinal(n):
    return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= n % 100 < 20 else n % 10, "th")

def list_spells():
    spells = db.load_spells()
    sorted_spells = sorted(spells, key=lambda s: s.get("name", "").lower())
    spell_entries = []
    for i, spell in enumerate(sorted_spells, start=1):
        entry = f"{i}. {spell.get('name','Unknown')}"
        spell_entries.append(entry)
    # Determine maximum width for each column.
    col_count = 5
    col_width = max(len(entry) for entry in spell_entries) + 4
    # Print table rows.
    total = len(spell_entries)
    print("\nAvailable Spells:")
    for row in range(0, total, col_count):
        row_items = spell_entries[row:row+col_count]
        print("".join(item.ljust(col_width) for item in row_items))
    return {str(i): spell for i, spell in enumerate(sorted_spells, start=1)}

def change_modifier():
    while True:
        new_mod = input("Enter new modifier (integer) (B to go back, X to exit): ").strip().lower()
        if new_mod == "b":
            return
        if new_mod == "x":
            exit("Exiting...")
        try:
            settings["modifier"] = int(new_mod)
            print(f"Modifier set to {settings['modifier']}.")
            return
        except ValueError:
            print("Invalid input.")

def main_loop():
    while True:
        print("\n===================================")
        print(f" Current modifier: {settings['modifier']}")
        print(" S - Show a single spell")
        print(" C - Compare spells")
        print(" M - Change modifier")
        print(" X - Exit")
        action = input("Your choice: ").strip().lower()
        if action == "x":
            break
        if action == "m":
            change_modifier()
            continue
        if action == "s":
            spells_dict = list_spells()
            choice = input("\nSelect a spell by number (B to go back, X to exit): ").strip().lower()
            if choice in ["x", "b"]:
                if choice == "x":
                    break
                continue
            if choice not in spells_dict:
                choice = "1"
            spell = spells_dict[choice]
            spell_full_name = spell.get("name", "Unknown")
            print(f"\nYou selected: {spell_full_name}")
            lvl = spell.get("level", 1)
            if lvl == 0:
                print(f"{spell_full_name} (cantrip) will be plotted for levels 1-4.")
            else:
                print(f"{spell_full_name} will be plotted for spell levels {lvl}-9.")
            mod = settings["modifier"]
            from plotting import plot_spell
            plot_spell(spell, mod, spell_full_name)
        elif action == "c":
            spells_dict = list_spells()
            prompt = "\nEnter spell numbers to compare (separated by spaces) (B to go back, X to exit): "
            selection = input(prompt).strip().lower()
            if selection in ["x", "b"]:
                if selection == "x":
                    break
                continue
            indices = selection.split()
            if len(indices) not in [2, 3]:
                print("Please select exactly 2 or 3 spells for comparison.")
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
            print("Invalid option. Please choose S, C, M or X.")

if __name__ == "__main__":
    main_loop()