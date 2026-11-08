"""Automated tests for Phase 2.2: Substage generation, >=2 mandatory enemy rooms on all paths,
Shrine 1-5 progression, Boss Arena gating, Room Ownership isolation, and Pause/Game Over flows.
"""

from __future__ import annotations

from pathlib import Path
import random
import pygame
import pytest

from characters.warrior import get_warrior_stats
from combat.abilities import MeleeAttackArc
from combat.combat_system import CombatSystem
from combat.damage import DamagePacket
from config.balance import (
    MIN_MANDATORY_ENEMY_ROOMS_PER_SUBSTAGE,
    SUBSTAGE_ROOM_COUNTS,
)
from entities.enemy import Enemy, EnemyState
from entities.player import Player
from entities.projectile import Projectile
from game.game import FracturedGateGame
from game.state_manager import GameState
from systems.progression import ProgressionManager
from systems.rng_streams import SeedHierarchy, derive_seed
from systems.run_manager import RunManager
from systems.save_system import SaveSystem
from world.biome import get_biome_config
from world.dungeon_generator import DungeonGenerator
from world.dungeon_graph import find_all_simple_paths
from world.room import RoomType
from world.tilemap import TileMap, TileType


def test_seed_hierarchy_determinism_and_isolation() -> None:
    """Verify SeedHierarchy produces deterministic and isolated streams per stage/substage/room."""
    h1 = SeedHierarchy(run_seed=424242)
    h2 = SeedHierarchy(run_seed=424242)
    h_diff = SeedHierarchy(run_seed=424243)

    assert derive_seed(424242, "stage", 1) == derive_seed(424242, "stage", 1)
    assert derive_seed(424242, "stage", 1) != derive_seed(424242, "stage", 2)

    # Calling room_content_rng or enemy_wave_rng in any order must not affect layout_rng
    _ = h1.enemy_wave_rng(1, 1, 3).randint(1, 1000)
    _ = h1.reward_rng(1, 1, 2).random()
    seq1 = [h1.layout_rng(1, 2).randint(0, 10000) for _ in range(10)]
    seq2 = [h2.layout_rng(1, 2).randint(0, 10000) for _ in range(10)]
    seq_diff = [h_diff.layout_rng(1, 2).randint(0, 10000) for _ in range(10)]

    assert seq1 == seq2
    assert seq1 != seq_diff


@pytest.mark.parametrize("seed", list(range(5001, 5051)))
def test_substage_generation_invariants_and_mandatory_enemy_paths(seed: int) -> None:
    """Verify 50 seeds of substage generation: room counts, non-overlap, connectivity,
    and >= 2 Mandatory Enemy Rooms on EVERY simple path from Entrance to Shrine.
    """
    stage_idx = ((seed - 5001) % 3) + 1
    substage_idx = ((seed - 5001) % 5) + 1
    biome = ["enchanted_forest", "crystal_cavern", "demon_castle"][stage_idx - 1]

    gen = DungeonGenerator(biome_id=biome)
    dungeon = gen.generate_substage(
        run_seed=seed,
        stage_index=stage_idx,
        substage_index=substage_idx,
    )

    min_r, max_r = SUBSTAGE_ROOM_COUNTS[substage_idx]
    assert min_r <= len(dungeon.rooms) <= max_r

    # 1 Entrance Room and 1 Shrine Room
    entrances = [r for r in dungeon.rooms if r.room_type == RoomType.ENTRANCE]
    shrines = [r for r in dungeon.rooms if r.room_type == RoomType.SHRINE]
    assert len(entrances) == 1
    assert len(shrines) == 1
    assert len(dungeon.shrine_rooms) == 1

    # Non-overlapping rooms
    for i, r_a in enumerate(dungeon.rooms):
        for r_b in dungeon.rooms[i + 1 :]:
            assert not r_a.intersects(r_b, padding=0)

    # Graph connectivity and every simple path from Entrance -> Shrine has >= 2 Mandatory Enemy Rooms
    room_by_id = {r.room_id: r for r in dungeon.rooms}
    all_paths = find_all_simple_paths(
        dungeon.graph,
        dungeon.entrance_room.room_id,
        dungeon.shrine_rooms[0].room_id,
    )
    assert len(all_paths) >= 1

    for path in all_paths:
        mandatory_enemy_rooms_on_path = [
            rid
            for rid in path[1:-1]
            if room_by_id[rid].is_mandatory and room_by_id[rid].room_type.is_enemy_room
        ]
        assert len(mandatory_enemy_rooms_on_path) >= MIN_MANDATORY_ENEMY_ROOMS_PER_SUBSTAGE, (
            f"Path {path} only had {len(mandatory_enemy_rooms_on_path)} mandatory enemy rooms!"
        )


def test_boss_room_inaccessible_before_fifth_shrine(tmp_path: Path) -> None:
    """Verify Boss Room cannot be entered until all 5 Shrines in the Stage are activated."""
    save_sys = SaveSystem(
        save_path=tmp_path / "profile.save.json",
        backup_path=tmp_path / "profile.save.bak",
    )
    prog = ProgressionManager(save_sys)
    run_mgr = RunManager(prog)
    run_mgr.start_new_run(character_id="warrior", seed=13579)

    for sub_idx in range(1, 5):
        assert run_mgr.current_substage_index == sub_idx
        assert run_mgr.can_enter_boss_room() is False
        with pytest.raises(RuntimeError):
            run_mgr._load_boss_arena(1)

        # Clear enemies and activate shrine
        for e in run_mgr.enemies:
            e.alive = False
        assert run_mgr.shrine_system is not None
        assert run_mgr.player is not None
        wx, wy = run_mgr.shrine_system.shrines[0].world_pos
        run_mgr.player.x, run_mgr.player.y = wx, wy
        ok, _ = run_mgr.try_activate_shrine()
        assert ok is True
        assert run_mgr.in_boss_room is False
        assert run_mgr.current_substage_index == sub_idx + 1

    # Now on Substage 5 before activating Shrine 5: still cannot enter boss room
    assert run_mgr.current_substage_index == 5
    assert run_mgr.stage_shrines_activated == 4
    assert run_mgr.can_enter_boss_room() is False
    with pytest.raises(RuntimeError):
        run_mgr._load_boss_arena(1)

    # Activate Shrine 5 -> immediately transitions to Boss Room
    for e in run_mgr.enemies:
        e.alive = False
    assert run_mgr.shrine_system is not None
    assert run_mgr.player is not None
    wx, wy = run_mgr.shrine_system.shrines[0].world_pos
    run_mgr.player.x, run_mgr.player.y = wx, wy
    ok, _ = run_mgr.try_activate_shrine()
    assert ok is True
    assert run_mgr.stage_shrines_activated == 5
    assert run_mgr.in_boss_room is True
    assert run_mgr.boss is not None


def test_room_ownership_ai_and_damage_isolation() -> None:
    """Verify enemies and attacks/projectiles are strictly isolated by room_id and room_bounds."""
    tilemap = TileMap(40, 40, get_biome_config("enchanted_forest"))
    for ty in range(2, 38):
        for tx in range(2, 38):
            tilemap.set_tile(tx, ty, TileType.FLOOR)
    combat = CombatSystem()
    rng = random.Random(99)

    player = Player(x=100.0, y=100.0, stats=get_warrior_stats())
    player.current_room_id = 1

    # Enemy in Room 2 right next to player's coordinates, plus a Dormant enemy in Room 1
    enemy_other_room = Enemy(
        x=108.0,
        y=100.0,
        archetype="melee",
        room_id=2,
        room_bounds=(80.0, 80.0, 160.0, 160.0),
    )
    enemy_dormant = Enemy(
        x=104.0,
        y=100.0,
        archetype="melee",
        room_id=1,
    )
    enemy_dormant.state = EnemyState.DORMANT

    enemy_same_room = Enemy(
        x=108.0,
        y=100.0,
        archetype="melee",
        room_id=1,
        room_bounds=(80.0, 80.0, 140.0, 140.0),
    )

    # 1. AI update: enemy_other_room must NOT chase/attack player in room 1; dormant enemy does nothing
    enemy_other_room.update(0.1, player, tilemap, combat, rng)
    assert enemy_other_room.state in (EnemyState.IDLE, EnemyState.PATROL)

    enemy_dormant.update(0.1, player, tilemap, combat, rng)
    assert enemy_dormant.state == EnemyState.DORMANT
    assert len(combat.melee_arcs) == 0

    # 2. Player melee attack in Room 1 hits enemy_same_room (Room 1), but NOT enemy_other_room (Room 2)
    combat.spawn_player_basic_attack(player, 1.0, 0.0)
    combat.update(0.05, player, [enemy_other_room, enemy_same_room], tilemap)
    assert enemy_other_room.hp == enemy_other_room.max_hp
    assert enemy_same_room.hp < enemy_same_room.max_hp

    # 3. Player projectile in Room 1 cannot hit enemy in Room 2
    combat.clear()
    combat.projectiles.append(
        Projectile(
            x=100.0,
            y=100.0,
            dir_x=1.0,
            dir_y=0.0,
            speed=200.0,
            damage=25,
            max_distance=100.0,
            owner_is_player=True,
            color=(255, 255, 255),
            room_id=1,
        )
    )
    combat.update(0.04, player, [enemy_other_room], tilemap)
    assert enemy_other_room.hp == enemy_other_room.max_hp

    # 4. Enemy melee arc / projectile from Room 2 cannot damage Player in Room 1
    combat.clear()
    initial_player_hp = player.hp
    combat.melee_arcs.append(
        MeleeAttackArc(
            owner_is_player=False,
            origin_x=100.0,
            origin_y=100.0,
            dir_x=1.0,
            dir_y=0.0,
            radius=40.0,
            arc_angle_rad=3.14,
            damage=20,
            knockback_force=50.0,
            duration=0.2,
            color=(255, 0, 0),
            room_id=2,
        )
    )
    combat.projectiles.append(
        Projectile(
            x=100.0,
            y=100.0,
            dir_x=1.0,
            dir_y=0.0,
            speed=100.0,
            damage=20,
            max_distance=100.0,
            owner_is_player=False,
            color=(255, 0, 0),
            room_id=2,
        )
    )
    combat.update(0.02, player, [enemy_other_room], tilemap)
    assert player.hp == initial_player_hp


def test_pause_resume_pause_quit_and_game_over_separation() -> None:
    """Verify Pause Resume preserves active run state, Pause Quit aborts cleanly,
    and Game Over is a separate flow.
    """
    game = FracturedGateGame(headless=True)
    game.run_manager.start_new_run(character_id="warrior", seed=77777)
    game.state_manager.change_state(GameState.GAMEPLAY)

    assert game.run_manager.player is not None
    game.run_manager.player.x += 12.0
    saved_x = game.run_manager.player.x
    saved_seed = game.run_manager.run_seed
    saved_stage = game.run_manager.current_stage_index
    saved_substage = game.run_manager.current_substage_index

    # 1. Pause -> Resume Run continues exact same run state
    game._handle_keydown(pygame.K_ESCAPE)
    assert game.state_manager.current_state == GameState.PAUSED
    game._handle_keydown(pygame.K_RETURN)  # Option 0: Resume Run
    assert game.state_manager.current_state == GameState.GAMEPLAY
    assert game.run_manager.is_run_active is True
    assert game.run_manager.run_seed == saved_seed
    assert game.run_manager.current_stage_index == saved_stage
    assert game.run_manager.current_substage_index == saved_substage
    assert game.run_manager.player.x == saved_x

    # 2. Pause -> Quit Run to Character Selection aborts run
    game._handle_keydown(pygame.K_ESCAPE)
    assert game.state_manager.current_state == GameState.PAUSED
    game._handle_keydown(pygame.K_DOWN)  # Select Option 1: Quit Run to Character Selection
    game._handle_keydown(pygame.K_RETURN)
    assert game.state_manager.current_state == GameState.CHARACTER_SELECTION
    assert game.run_manager.is_run_active is False
    assert game.run_manager.run_outcome == "aborted"

    # 3. Start a new run and test Game Over flow
    game.run_manager.start_new_run(character_id="warrior", seed=88888)
    game.state_manager.change_state(GameState.GAMEPLAY)
    assert game.run_manager.player is not None
    game.run_manager.player.take_damage(
        DamagePacket(amount=9999, source_x=0.0, source_y=0.0)
    )
    assert game.run_manager.player.alive is False
    # Advance animation until one-shot DEATH finishes
    for _ in range(25):
        game.run_manager.player.anim_controller.update(0.1)
    game.update(0.016)
    assert game.state_manager.current_state == GameState.GAME_OVER
    assert game.run_manager.is_run_active is False
    assert game.run_manager.run_outcome == "game_over"
    pygame.quit()
