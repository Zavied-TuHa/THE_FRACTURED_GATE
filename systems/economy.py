"""Game economy manager for Gold (skills) and Blue Crystals (characters)."""

from __future__ import annotations

from config.balance import CHARACTER_UNLOCK_COSTS, SKILL_UNLOCK_COSTS
from systems.save_system import SaveData


class EconomyManager:
    """Manages currency transactions and cost queries."""

    @staticmethod
    def get_character_unlock_cost(character_id: str) -> int:
        """Return Blue Crystal cost required to unlock a character."""
        return int(CHARACTER_UNLOCK_COSTS.get(character_id, 50))

    @staticmethod
    def get_skill_unlock_cost(character_id: str, skill_slot_key: str) -> int:
        """Return Gold cost required to unlock skill_1 or skill_2 for a character."""
        char_costs = SKILL_UNLOCK_COSTS.get(character_id, {})
        return int(char_costs.get(skill_slot_key, 100))

    @staticmethod
    def add_currencies(save_data: SaveData, gold: int = 0, blue_crystals: int = 0) -> None:
        """Add Gold and/or Blue Crystals to persistent SaveData."""
        if gold > 0:
            save_data.gold += gold
        if blue_crystals > 0:
            save_data.blue_crystals += blue_crystals

    @staticmethod
    def can_afford_character(save_data: SaveData, character_id: str) -> bool:
        """Check if the player has enough Blue Crystals to unlock character_id."""
        cost = EconomyManager.get_character_unlock_cost(character_id)
        return save_data.blue_crystals >= cost

    @staticmethod
    def can_afford_skill(
        save_data: SaveData,
        character_id: str,
        skill_slot_key: str,
    ) -> bool:
        """Check if the player has enough Gold to unlock skill_slot_key."""
        cost = EconomyManager.get_skill_unlock_cost(character_id, skill_slot_key)
        return save_data.gold >= cost
