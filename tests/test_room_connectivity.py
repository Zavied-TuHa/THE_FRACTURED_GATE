"""Automated tests verifying graph connectivity, corridor carving, and tile walkability."""

from __future__ import annotations

import pytest

from world.dungeon_generator import DungeonGenerator


@pytest.mark.parametrize("seed", range(200, 305))
def test_100_plus_seeds_graph_and_tile_reachability(seed: int) -> None:
    """Verify across 105 seeds that all rooms, shrines, and the boss room are reachable."""
    biome_cycle = ("enchanted_forest", "crystal_cavern", "demon_castle")
    biome_id = biome_cycle[seed % 3]
    dungeon = DungeonGenerator(biome_id).generate(seed=seed * 3571)

    # 1. Graph-level connectivity: all rooms reachable from Entrance
    assert dungeon.graph.is_fully_connected(), f"Seed {seed}: DungeonGraph is disconnected"
    for room in dungeon.rooms:
        path = dungeon.graph.find_path(dungeon.entrance_room.room_id, room.room_id)
        assert len(path) >= 1, f"Seed {seed}: No graph path to room {room.room_id}"

    # 2. Tile-level walkability BEFORE boss gate unlock:
    # Entrance must reach all 3 shrines without passing through locked boss gates
    reachable_before_unlock = dungeon.tilemap.reachable_tiles_from(
        dungeon.entrance_room.center,
        ignore_boss_lock=False,
    )
    for shrine_pos in dungeon.shrine_positions:
        assert shrine_pos in reachable_before_unlock, (
            f"Seed {seed}: Shrine at {shrine_pos} is blocked before boss unlock!"
        )

    # 3. Tile-level walkability AFTER unlocking boss gates:
    # Entrance must reach every single room center including the Boss Room
    dungeon.tilemap.unlock_boss_gates()
    reachable_after_unlock = dungeon.tilemap.reachable_tiles_from(
        dungeon.entrance_room.center,
        ignore_boss_lock=False,
    )
    for room in dungeon.rooms:
        assert room.center in reachable_after_unlock, (
            f"Seed {seed}: Room {room.room_id} ({room.room_type}) unreachable at tile level"
        )
    assert dungeon.boss_room.center in reachable_after_unlock
