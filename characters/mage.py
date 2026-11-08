"""Mage character definition (Magic Damage Dealer, unlocked with Blue Crystals)."""

from __future__ import annotations

from characters.character_data import CharacterStats
from config.settings import COLOR_PLAYER_MAGE


def get_mage_stats() -> CharacterStats:
    """Return the data-driven CharacterStats for the Mage."""
    return CharacterStats.from_config(
        character_id="mage",
        color=COLOR_PLAYER_MAGE,
        is_ranged_basic=True,
    )
