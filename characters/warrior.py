"""Warrior character definition (Melee Fighter, unlocked by default)."""

from __future__ import annotations

from characters.character_data import CharacterStats
from config.settings import COLOR_PLAYER_WARRIOR


def get_warrior_stats() -> CharacterStats:
    """Return the data-driven CharacterStats for the Warrior."""
    return CharacterStats.from_config(
        character_id="warrior",
        color=COLOR_PLAYER_WARRIOR,
        is_ranged_basic=False,
    )
