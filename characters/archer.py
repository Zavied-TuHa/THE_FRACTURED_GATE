"""Archer character definition (Ranged Damage Dealer, unlocked with Blue Crystals)."""

from __future__ import annotations

from characters.character_data import CharacterStats
from config.settings import COLOR_PLAYER_ARCHER


def get_archer_stats() -> CharacterStats:
    """Return the data-driven CharacterStats for the Archer."""
    return CharacterStats.from_config(
        character_id="archer",
        color=COLOR_PLAYER_ARCHER,
        is_ranged_basic=True,
    )


def get_all_character_stats() -> dict[str, CharacterStats]:
    """Return a dictionary mapping character_id to its CharacterStats."""
    from characters.mage import get_mage_stats
    from characters.warrior import get_warrior_stats

    return {
        "warrior": get_warrior_stats(),
        "mage": get_mage_stats(),
        "archer": get_archer_stats(),
    }
