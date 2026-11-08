"""Data-driven character stats and skill definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.balance import CHARACTER_CONFIGS


@dataclass(frozen=True)
class SkillDefinition:
    """Data-driven definition for an active character skill."""

    skill_id: str
    name: str
    description: str
    cooldown: float
    damage_multiplier: float
    attack_range: float
    unlocked_by_default: bool


@dataclass(frozen=True)
class CharacterStats:
    """Complete data-driven definition for a playable character class."""

    character_id: str
    name: str
    role: str
    unlocked_by_default: bool
    max_hp: int
    move_speed: float
    attack_damage: int
    attack_cooldown: float
    attack_range: float
    dash_speed: float
    dash_duration: float
    dash_cooldown: float
    is_ranged_basic: bool
    color: tuple[int, int, int]
    skill_1: SkillDefinition
    skill_2: SkillDefinition

    @classmethod
    def from_config(
        cls,
        character_id: str,
        color: tuple[int, int, int],
        is_ranged_basic: bool = False,
    ) -> CharacterStats:
        """Build a CharacterStats instance from config.balance.CHARACTER_CONFIGS."""
        raw: dict[str, Any] = CHARACTER_CONFIGS[character_id]
        s1_raw: dict[str, Any] = raw["skill_1"]
        s2_raw: dict[str, Any] = raw["skill_2"]

        skill_1 = SkillDefinition(
            skill_id=str(s1_raw["id"]),
            name=str(s1_raw["name"]),
            description=str(s1_raw["description"]),
            cooldown=float(s1_raw["cooldown"]),
            damage_multiplier=float(s1_raw["damage_multiplier"]),
            attack_range=float(s1_raw["range"]),
            unlocked_by_default=bool(s1_raw["unlocked_by_default"]),
        )
        skill_2 = SkillDefinition(
            skill_id=str(s2_raw["id"]),
            name=str(s2_raw["name"]),
            description=str(s2_raw["description"]),
            cooldown=float(s2_raw["cooldown"]),
            damage_multiplier=float(s2_raw["damage_multiplier"]),
            attack_range=float(s2_raw["range"]),
            unlocked_by_default=bool(s2_raw["unlocked_by_default"]),
        )

        return cls(
            character_id=str(raw["id"]),
            name=str(raw["name"]),
            role=str(raw["role"]),
            unlocked_by_default=bool(raw["unlocked_by_default"]),
            max_hp=int(raw["max_hp"]),
            move_speed=float(raw["move_speed"]),
            attack_damage=int(raw["attack_damage"]),
            attack_cooldown=float(raw["attack_cooldown"]),
            attack_range=float(raw["attack_range"]),
            dash_speed=float(raw["dash_speed"]),
            dash_duration=float(raw["dash_duration"]),
            dash_cooldown=float(raw["dash_cooldown"]),
            is_ranged_basic=is_ranged_basic,
            color=color,
            skill_1=skill_1,
            skill_2=skill_2,
        )
