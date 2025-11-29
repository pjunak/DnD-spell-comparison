PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS spells;

CREATE TABLE IF NOT EXISTS spells (
    name TEXT PRIMARY KEY,
    level INTEGER NOT NULL,
    school TEXT,
    casting_time TEXT,
    range TEXT,
    duration TEXT,
    components TEXT,
    primary_effect TEXT NOT NULL,
    secondary_effect TEXT,
    modifiers TEXT NOT NULL DEFAULT '[]'
);

DROP TABLE IF EXISTS cantrips;

CREATE TABLE IF NOT EXISTS cantrips (
    name TEXT PRIMARY KEY,
    school TEXT,
    casting_time TEXT,
    range TEXT,
    duration TEXT,
    components TEXT,
    primary_effect TEXT NOT NULL,
    secondary_effect TEXT,
    scaling_levels TEXT NOT NULL,
    modifiers TEXT NOT NULL DEFAULT '[]'
);

DROP TABLE IF EXISTS bonuses;
DROP TABLE IF EXISTS modifiers;

CREATE TABLE IF NOT EXISTS modifiers (
    name TEXT PRIMARY KEY,
    category TEXT,
    scope TEXT NOT NULL DEFAULT 'spell',
    description TEXT,
    applies_to TEXT,
    effect_data TEXT,
    default_enabled INTEGER NOT NULL DEFAULT 0
);
