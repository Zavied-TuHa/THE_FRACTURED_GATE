"""Persistent JSON save system with schema validation and corrupted-file backup recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
from typing import Any

from config.balance import STARTING_BLUE_CRYSTALS, STARTING_GOLD
from config.settings import SAVE_BACKUP_PATH, SAVE_FILE_PATH


@dataclass
class SaveData:
    """Validated player profile and permanent progression state."""

    gold: int = STARTING_GOLD
    blue_crystals: int = STARTING_BLUE_CRYSTALS
    unlocked_characters: list[str] = field(default_factory=lambda: ["warrior"])
    unlocked_skills: dict[str, list[str]] = field(
        default_factory=lambda: {
            "warrior": [],
            "mage": [],
            "archer": [],
        }
    )
    runs_started: int = 0
    runs_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize SaveData to a JSON-compatible dictionary."""
        return {
            "version": 1,
            "gold": int(max(0, self.gold)),
            "blue_crystals": int(max(0, self.blue_crystals)),
            "unlocked_characters": list(dict.fromkeys(self.unlocked_characters)),
            "unlocked_skills": {
                k: list(dict.fromkeys(v)) for k, v in self.unlocked_skills.items()
            },
            "runs_started": int(max(0, self.runs_started)),
            "runs_completed": int(max(0, self.runs_completed)),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SaveData:
        """Validate and construct SaveData from a raw parsed JSON dictionary."""
        if not isinstance(raw, dict):
            raise ValueError("Save file root must be a JSON object.")

        gold = int(raw.get("gold", STARTING_GOLD))
        crystals = int(raw.get("blue_crystals", STARTING_BLUE_CRYSTALS))
        if gold < 0 or crystals < 0:
            raise ValueError("Currency values cannot be negative.")

        unlocked_chars = raw.get("unlocked_characters", ["warrior"])
        if not isinstance(unlocked_chars, list) or not all(
            isinstance(c, str) for c in unlocked_chars
        ):
            raise ValueError("Invalid unlocked_characters list.")
        if "warrior" not in unlocked_chars:
            unlocked_chars.insert(0, "warrior")

        raw_skills = raw.get("unlocked_skills", {})
        if not isinstance(raw_skills, dict):
            raise ValueError("Invalid unlocked_skills dictionary.")

        unlocked_skills: dict[str, list[str]] = {
            "warrior": [],
            "mage": [],
            "archer": [],
        }
        for char_id in ("warrior", "mage", "archer"):
            char_skills = raw_skills.get(char_id, [])
            if isinstance(char_skills, list):
                unlocked_skills[char_id] = [
                    str(s) for s in char_skills if s in ("skill_1", "skill_2")
                ]

        runs_started = max(0, int(raw.get("runs_started", 0)))
        runs_completed = max(0, int(raw.get("runs_completed", 0)))

        return cls(
            gold=gold,
            blue_crystals=crystals,
            unlocked_characters=unlocked_chars,
            unlocked_skills=unlocked_skills,
            runs_started=runs_started,
            runs_completed=runs_completed,
        )


class SaveSystem:
    """Handles reading, validating, backing up, and writing persistent save data."""

    def __init__(
        self,
        save_path: Path = SAVE_FILE_PATH,
        backup_path: Path = SAVE_BACKUP_PATH,
    ) -> None:
        self.save_path: Path = save_path
        self.backup_path: Path = backup_path

    def load(self) -> SaveData:
        """Load save file; fall back to backup or default SaveData if corrupted."""
        for candidate in (self.save_path, self.backup_path):
            if not candidate.exists():
                continue
            try:
                content = candidate.read_text(encoding="utf-8")
                parsed = json.loads(content)
                data = SaveData.from_dict(parsed)
                if candidate == self.backup_path:
                    self.save(data)
                return data
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                continue

        default_data = SaveData()
        self.save(default_data)
        return default_data

    def save(self, data: SaveData) -> None:
        """Persist SaveData atomically while maintaining a valid backup file."""
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        if self.save_path.exists():
            try:
                # Only overwrite backup if current save file is valid JSON
                existing_raw = json.loads(self.save_path.read_text(encoding="utf-8"))
                SaveData.from_dict(existing_raw)
                shutil.copy2(self.save_path, self.backup_path)
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                pass

        payload = json.dumps(data.to_dict(), indent=2)
        self.save_path.write_text(payload, encoding="utf-8")
