"""Permanent progression system managing character and skill unlocks."""

from __future__ import annotations

from systems.economy import EconomyManager
from systems.save_system import SaveData, SaveSystem


class ProgressionManager:
    """Coordinates persistent unlocks for characters (Blue Crystals) and skills (Gold)."""

    def __init__(self, save_system: SaveSystem) -> None:
        self.save_system: SaveSystem = save_system
        self.data: SaveData = self.save_system.load()

    def reload(self) -> None:
        """Reload save data from disk."""
        self.data = self.save_system.load()

    def persist(self) -> None:
        """Save current progression data to disk."""
        self.save_system.save(self.data)

    def is_character_unlocked(self, character_id: str) -> bool:
        """Return True if character_id is unlocked."""
        return character_id in self.data.unlocked_characters

    def is_skill_unlocked(self, character_id: str, skill_slot_key: str) -> bool:
        """Return True if skill_slot_key ('skill_1' or 'skill_2') is unlocked."""
        return skill_slot_key in self.data.unlocked_skills.get(character_id, [])

    def unlock_character(self, character_id: str) -> bool:
        """Spend Blue Crystals to permanently unlock a character if affordable."""
        if self.is_character_unlocked(character_id):
            return False
        cost = EconomyManager.get_character_unlock_cost(character_id)
        if self.data.blue_crystals < cost:
            return False

        self.data.blue_crystals -= cost
        self.data.unlocked_characters.append(character_id)
        self.persist()
        return True

    def unlock_skill(self, character_id: str, skill_slot_key: str) -> bool:
        """Spend Gold to permanently unlock a character skill if affordable."""
        if not self.is_character_unlocked(character_id):
            return False
        if skill_slot_key not in ("skill_1", "skill_2"):
            return False
        if self.is_skill_unlocked(character_id, skill_slot_key):
            return False

        cost = EconomyManager.get_skill_unlock_cost(character_id, skill_slot_key)
        if self.data.gold < cost:
            return False

        self.data.gold -= cost
        self.data.unlocked_skills.setdefault(character_id, []).append(skill_slot_key)
        self.persist()
        return True

    def grant_rewards(self, gold: int = 0, blue_crystals: int = 0) -> None:
        """Add Gold and Blue Crystals and immediately save progression."""
        EconomyManager.add_currencies(self.data, gold=gold, blue_crystals=blue_crystals)
        self.persist()
