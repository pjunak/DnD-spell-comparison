import sqlite3
import json

DB_FILE = "spellBook.db"

def load_spells():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM spells")
    rows = cur.fetchall()
    conn.close()
    spells = []
    for row in rows:
        spell = dict(row)
        if "components" in spell and isinstance(spell["components"], str):
            try:
                spell["components"] = json.loads(spell["components"])
            except Exception:
                spell["components"] = spell["components"].split(',')
        if "bonus_options" in spell and isinstance(spell["bonus_options"], str):
            try:
                spell["bonus_options"] = json.loads(spell["bonus_options"])
            except Exception:
                spell["bonus_options"] = []
        if "effects" in spell and isinstance(spell["effects"], str):
            try:
                spell["effects"] = json.loads(spell["effects"])
            except Exception:
                spell["effects"] = []
        spells.append(spell)
    return spells