"""Data-driven gameplay balance, economy prices, character stats, and enemy stats."""

from __future__ import annotations

from typing import Any

# Economy Configuration
STARTING_GOLD: int = 0
STARTING_BLUE_CRYSTALS: int = 0

SHRINE_REWARD_GOLD: int = 25
SHRINE_REWARD_CRYSTALS: int = 5

BOSS_REWARD_GOLD: int = 60
BOSS_REWARD_CRYSTALS: int = 15

TREASURE_CHEST_GOLD: int = 150
TREASURE_CHEST_CRYSTALS: int = 50

ENEMY_DROP_TABLE: dict[str, dict[str, int]] = {
    "melee": {"gold": 5, "crystals": 0},
    "ranged": {"gold": 7, "crystals": 0},
    "fast": {"gold": 6, "crystals": 0},
    "elite": {"gold": 20, "crystals": 3},
    "mini_boss": {"gold": 35, "crystals": 8},
    "boss": {"gold": 60, "crystals": 15},
}

# Unlock Costs
CHARACTER_UNLOCK_COSTS: dict[str, int] = {
    "warrior": 0,      # Unlocked by default
    "mage": 50,        # Blue crystals
    "archer": 50,      # Blue crystals
}

SKILL_UNLOCK_COSTS: dict[str, dict[str, int]] = {
    "warrior": {"skill_1": 100, "skill_2": 200},
    "mage": {"skill_1": 120, "skill_2": 240},
    "archer": {"skill_1": 110, "skill_2": 220},
}

# Playable Character Definitions
CHARACTER_CONFIGS: dict[str, dict[str, Any]] = {
    "warrior": {
        "id": "warrior",
        "name": "Warrior",
        "role": "Melee Fighter",
        "unlocked_by_default": True,
        "max_hp": 120,
        "move_speed": 95.0,
        "attack_damage": 24,
        "attack_cooldown": 0.40,
        "attack_range": 26.0,
        "dash_speed": 250.0,
        "dash_duration": 0.16,
        "dash_cooldown": 0.90,
        "skill_1": {
            "id": "cleave_strike",
            "name": "Crimson Cleave",
            "description": "Wide heavy arc dealing 180% melee damage with high knockback.",
            "cooldown": 4.0,
            "damage_multiplier": 1.8,
            "range": 34.0,
            "unlocked_by_default": False,
        },
        "skill_2": {
            "id": "iron_tempest",
            "name": "Iron Tempest",
            "description": "360-degree shockwave damaging and repelling all nearby foes.",
            "cooldown": 8.0,
            "damage_multiplier": 2.4,
            "range": 48.0,
            "unlocked_by_default": False,
        },
    },
    "mage": {
        "id": "mage",
        "name": "Mage",
        "role": "Magic Damage Dealer",
        "unlocked_by_default": False,
        "max_hp": 80,
        "move_speed": 88.0,
        "attack_damage": 28,
        "attack_cooldown": 0.50,
        "attack_range": 140.0,
        "dash_speed": 260.0,
        "dash_duration": 0.15,
        "dash_cooldown": 1.00,
        "skill_1": {
            "id": "arcane_nova",
            "name": "Arcane Nova",
            "description": "Unleash a burst of arcane projectiles in 8 directions.",
            "cooldown": 5.0,
            "damage_multiplier": 1.6,
            "range": 120.0,
            "unlocked_by_default": False,
        },
        "skill_2": {
            "id": "void_cataclysm",
            "name": "Void Cataclysm",
            "description": "Detonate dark energy around the caster for massive damage.",
            "cooldown": 10.0,
            "damage_multiplier": 2.8,
            "range": 70.0,
            "unlocked_by_default": False,
        },
    },
    "archer": {
        "id": "archer",
        "name": "Archer",
        "role": "Ranged Damage Dealer",
        "unlocked_by_default": False,
        "max_hp": 95,
        "move_speed": 108.0,
        "attack_damage": 20,
        "attack_cooldown": 0.32,
        "attack_range": 160.0,
        "dash_speed": 280.0,
        "dash_duration": 0.14,
        "dash_cooldown": 0.75,
        "skill_1": {
            "id": "piercing_volley",
            "name": "Piercing Volley",
            "description": "Fire a spread of 3 high-velocity arrows.",
            "cooldown": 3.5,
            "damage_multiplier": 1.5,
            "range": 160.0,
            "unlocked_by_default": False,
        },
        "skill_2": {
            "id": "shadow_barrage",
            "name": "Shadow Barrage",
            "description": "Fire a ring of shadow arrows and reset dash cooldown.",
            "cooldown": 7.5,
            "damage_multiplier": 2.2,
            "range": 150.0,
            "unlocked_by_default": False,
        },
    },
}

# Enemy Archetype Definitions
ENEMY_CONFIGS: dict[str, dict[str, Any]] = {
    "melee": {
        "name": "Crypt Ghoul",
        "max_hp": 50,
        "move_speed": 52.0,
        "damage": 12,
        "attack_range": 16.0,
        "detection_range": 135.0,
        "attack_cooldown": 1.0,
        "knockback_resist": 0.0,
        "size": 12,
    },
    "ranged": {
        "name": "Acolyte Cultist",
        "max_hp": 36,
        "move_speed": 42.0,
        "damage": 10,
        "attack_range": 125.0,
        "detection_range": 155.0,
        "attack_cooldown": 1.6,
        "projectile_speed": 135.0,
        "knockback_resist": 0.0,
        "size": 12,
    },
    "fast": {
        "name": "Shadow Stalker",
        "max_hp": 30,
        "move_speed": 82.0,
        "damage": 9,
        "attack_range": 14.0,
        "detection_range": 150.0,
        "attack_cooldown": 0.7,
        "knockback_resist": 0.0,
        "size": 10,
    },
    "elite": {
        "name": "Dread Executioner",
        "max_hp": 130,
        "move_speed": 46.0,
        "damage": 22,
        "attack_range": 22.0,
        "detection_range": 160.0,
        "attack_cooldown": 1.25,
        "knockback_resist": 0.45,
        "size": 16,
    },
    "mini_boss": {
        "name": "Gate Warden",
        "max_hp": 200,
        "move_speed": 50.0,
        "damage": 25,
        "attack_range": 24.0,
        "detection_range": 180.0,
        "attack_cooldown": 1.15,
        "knockback_resist": 0.6,
        "size": 18,
    },
    "boss": {
        "name": "Malakor, Sovereign of the Gate",
        "max_hp": 360,
        "move_speed": 56.0,
        "damage": 28,
        "attack_range": 28.0,
        "detection_range": 240.0,
        "attack_cooldown": 1.1,
        "projectile_speed": 150.0,
        "knockback_resist": 0.75,
        "size": 22,
    },
}

# Run, Stage & Substage Requirements (Revision 2.0)
REQUIRED_SHRINES_PER_STAGE: int = 3  # Preserved for legacy single-map generator tests
TOTAL_STAGES_PER_RUN: int = 3
SUBSTAGES_PER_STAGE: int = 5
SHRINES_PER_SUBSTAGE: int = 1
REQUIRED_SHRINES_PER_STAGE_V2: int = SUBSTAGES_PER_STAGE * SHRINES_PER_SUBSTAGE  # 5 Shrines/Stage
TOTAL_SUBSTAGES_PER_RUN: int = TOTAL_STAGES_PER_RUN * SUBSTAGES_PER_STAGE  # 15 Substages/Run
TOTAL_SHRINES_PER_RUN: int = TOTAL_STAGES_PER_RUN * REQUIRED_SHRINES_PER_STAGE_V2  # 15 Shrines/Run
MIN_MANDATORY_ENEMY_ROOMS_PER_SUBSTAGE: int = 2

# Variable room count ranges (min_rooms, max_rooms) by Substage index (1..5)
SUBSTAGE_ROOM_COUNTS: dict[int, tuple[int, int]] = {
    1: (6, 8),
    2: (7, 9),
    3: (8, 10),
    4: (8, 11),
    5: (9, 12),
}

# Configurable distribution weights for optional branch rooms in a Substage
OPTIONAL_ROOM_WEIGHTS: dict[str, float] = {
    "enemy": 0.45,
    "special": 0.20,
    "shop": 0.15,
    "chest": 0.20,
}
