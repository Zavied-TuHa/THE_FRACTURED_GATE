"""Biome definitions and procedural generation parameters per stage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BiomeConfig:
    """Configuration parameters for a stage biome."""

    biome_id: str
    name: str
    grid_width: int
    grid_height: int
    min_rooms: int
    max_rooms: int
    min_room_size: int
    max_room_size: int
    corridor_width: int
    room_padding: int
    extra_loop_chance: float
    floor_color: tuple[int, int, int]
    floor_accent_color: tuple[int, int, int]
    corridor_color: tuple[int, int, int]
    wall_top_color: tuple[int, int, int]
    wall_front_color: tuple[int, int, int]
    ambient_tint: tuple[int, int, int]
    boss_name: str


BIOMES: dict[str, BiomeConfig] = {
    "enchanted_forest": BiomeConfig(
        biome_id="enchanted_forest",
        name="Enchanted Forest",
        grid_width=96,
        grid_height=96,
        min_rooms=10,
        max_rooms=13,
        min_room_size=9,
        max_room_size=15,
        corridor_width=3,
        room_padding=3,
        extra_loop_chance=0.25,
        floor_color=(28, 38, 32),
        floor_accent_color=(36, 49, 40),
        corridor_color=(24, 33, 28),
        wall_top_color=(15, 22, 18),
        wall_front_color=(42, 60, 48),
        ambient_tint=(180, 220, 195),
        boss_name="Sylvanus, Blighted Elder",
    ),
    "crystal_cavern": BiomeConfig(
        biome_id="crystal_cavern",
        name="Crystal Cavern",
        grid_width=100,
        grid_height=100,
        min_rooms=11,
        max_rooms=14,
        min_room_size=8,
        max_room_size=14,
        corridor_width=2,
        room_padding=3,
        extra_loop_chance=0.30,
        floor_color=(26, 30, 46),
        floor_accent_color=(35, 42, 64),
        corridor_color=(22, 26, 40),
        wall_top_color=(14, 17, 28),
        wall_front_color=(46, 56, 86),
        ambient_tint=(175, 205, 245),
        boss_name="Vaelrix, Crystalline Behemoth",
    ),
    "demon_castle": BiomeConfig(
        biome_id="demon_castle",
        name="Demon Castle",
        grid_width=108,
        grid_height=108,
        min_rooms=12,
        max_rooms=15,
        min_room_size=10,
        max_room_size=16,
        corridor_width=3,
        room_padding=3,
        extra_loop_chance=0.20,
        floor_color=(38, 26, 32),
        floor_accent_color=(48, 32, 40),
        corridor_color=(32, 22, 27),
        wall_top_color=(20, 12, 16),
        wall_front_color=(64, 38, 48),
        ambient_tint=(235, 175, 185),
        boss_name="Malakor, Sovereign of the Gate",
    ),
}


def get_biome_config(biome_id: str) -> BiomeConfig:
    """Retrieve a biome configuration by ID, defaulting to Enchanted Forest."""
    return BIOMES.get(biome_id, BIOMES["enchanted_forest"])
