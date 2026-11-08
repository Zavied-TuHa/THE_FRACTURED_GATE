"""Comprehensive automated tests for procedural dungeon generation across 100+ seeds."""

from __future__ import annotations

import pytest

from config.balance import REQUIRED_SHRINES_PER_STAGE
from world.dungeon_generator import DungeonGenerator
from world.room import RoomType


BIOME_IDS = ("enchanted_forest", "crystal_cavern", "demon_castle")


def test_deterministic_same_seed_produces_identical_dungeon() -> None:
    """Verify that the same random seed produces the exact same room layout and tilemap."""
    gen = DungeonGenerator("enchanted_forest")
    d1 = gen.generate(seed=424242)
    d2 = gen.generate(seed=424242)

    assert len(d1.rooms) == len(d2.rooms)
    for r1, r2 in zip(d1.rooms, d2.rooms):
        assert (r1.x, r1.y, r1.width, r1.height, r1.room_type) == (
            r2.x,
            r2.y,
            r2.width,
            r2.height,
            r2.room_type,
        )
    assert d1.shrine_positions == d2.shrine_positions
    assert d1.tilemap.grid == d2.tilemap.grid


def test_different_seeds_produce_different_layouts() -> None:
    """Verify that distinct random seeds generate distinct dungeon layouts."""
    gen = DungeonGenerator("crystal_cavern")
    d1 = gen.generate(seed=1001)
    d2 = gen.generate(seed=2002)

    layout_1 = [(r.x, r.y, r.width, r.height) for r in d1.rooms]
    layout_2 = [(r.x, r.y, r.width, r.height) for r in d2.rooms]
    assert layout_1 != layout_2


@pytest.mark.parametrize("seed", range(1, 105))
def test_100_plus_seeds_structural_invariants(seed: int) -> None:
    """Test 104 distinct seeds across biomes for non-overlap, shrines, entrance, and boss."""
    biome_id = BIOME_IDS[seed % len(BIOME_IDS)]
    gen = DungeonGenerator(biome_id=biome_id)
    dungeon = gen.generate(seed=seed * 7919)

    # 1. Rooms must not overlap
    for i, room_a in enumerate(dungeon.rooms):
        for room_b in dungeon.rooms[i + 1 :]:
            assert not room_a.intersects(room_b, padding=0), (
                f"Seed {seed}: Room {room_a.room_id} overlaps Room {room_b.room_id}"
            )

    # 2. Exactly one Entrance room and one Boss room must exist
    entrance_rooms = [r for r in dungeon.rooms if r.room_type == RoomType.ENTRANCE]
    boss_rooms = [r for r in dungeon.rooms if r.room_type == RoomType.BOSS]
    assert len(entrance_rooms) == 1
    assert len(boss_rooms) == 1
    assert dungeon.entrance_room.room_id != dungeon.boss_room.room_id

    # 3. Exactly 3 Shrine objectives must be generated
    shrine_rooms = [r for r in dungeon.rooms if r.room_type == RoomType.SHRINE]
    assert len(shrine_rooms) == REQUIRED_SHRINES_PER_STAGE
    assert len(dungeon.shrine_positions) == REQUIRED_SHRINES_PER_STAGE
    assert len(set(dungeon.shrine_positions)) == REQUIRED_SHRINES_PER_STAGE
