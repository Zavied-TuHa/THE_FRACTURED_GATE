"""Automated tests for SaveSystem, EconomyManager, and ProgressionManager."""

from __future__ import annotations

from pathlib import Path

from systems.progression import ProgressionManager
from systems.save_system import SaveSystem


def test_default_save_and_initial_character_unlocks(tmp_path: Path) -> None:
    """Verify initial prototype state: Warrior unlocked, Mage/Archer/skills locked."""
    save_file = tmp_path / "profile.save.json"
    backup_file = tmp_path / "profile.save.bak"
    save_sys = SaveSystem(save_path=save_file, backup_path=backup_file)
    prog = ProgressionManager(save_sys)

    assert prog.is_character_unlocked("warrior") is True
    assert prog.is_character_unlocked("mage") is False
    assert prog.is_character_unlocked("archer") is False
    assert prog.is_skill_unlocked("warrior", "skill_1") is False
    assert prog.is_skill_unlocked("warrior", "skill_2") is False
    assert prog.data.gold == 0
    assert prog.data.blue_crystals == 0


def test_currency_persistence_and_unlocking_characters_and_skills(tmp_path: Path) -> None:
    """Verify unlocking characters with Blue Crystals and skills with Gold persists."""
    save_file = tmp_path / "profile.save.json"
    backup_file = tmp_path / "profile.save.bak"
    save_sys = SaveSystem(save_path=save_file, backup_path=backup_file)
    prog = ProgressionManager(save_sys)

    prog.grant_rewards(gold=350, blue_crystals=60)
    assert prog.unlock_character("mage") is True
    assert prog.is_character_unlocked("mage") is True
    assert prog.data.blue_crystals == 10

    assert prog.unlock_skill("warrior", "skill_1") is True
    assert prog.unlock_skill("warrior", "skill_2") is True
    assert prog.is_skill_unlocked("warrior", "skill_1") is True
    assert prog.is_skill_unlocked("warrior", "skill_2") is True
    assert prog.data.gold == 50

    # Reload from disk and verify persistence
    reloaded = ProgressionManager(save_sys)
    assert reloaded.is_character_unlocked("mage") is True
    assert reloaded.is_skill_unlocked("warrior", "skill_1") is True
    assert reloaded.is_skill_unlocked("warrior", "skill_2") is True
    assert reloaded.data.gold == 50
    assert reloaded.data.blue_crystals == 10


def test_corrupted_save_recovers_from_backup(tmp_path: Path) -> None:
    """Verify that a corrupted main save file recovers seamlessly from its backup."""
    save_file = tmp_path / "profile.save.json"
    backup_file = tmp_path / "profile.save.bak"
    save_sys = SaveSystem(save_path=save_file, backup_path=backup_file)
    prog = ProgressionManager(save_sys)

    prog.grant_rewards(gold=200, blue_crystals=75)
    # Second save writes the valid previous state into backup_file
    prog.grant_rewards(gold=25, blue_crystals=5)

    # Corrupt primary save file
    save_file.write_text("{corrupted_json: true", encoding="utf-8")

    recovered = ProgressionManager(save_sys)
    assert recovered.data.gold >= 200
    assert recovered.data.blue_crystals >= 75
