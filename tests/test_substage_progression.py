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
    REQUIRED_SHRINES_PER_STAGE_V2,
    SHRINES_PER_SUBSTAGE,
    SUBSTAGES_PER_STAGE,
    SUBSTAGE_ROOM_COUNTS,
    TOTAL_SHRINES_PER_RUN,
    TOTAL_STAGES_PER_RUN,
    TOTAL_SUBSTAGES_PER_RUN,
)
from config.settings import TILE_SIZE
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
    """Verify Main Menu -> Hub Room, Pause Resume, Pause Quit Confirmation -> Hub Room,
    Final Treasure Room -> Hub Room, and Game Over -> Hub Room flows.
    """
    game = FracturedGateGame(headless=True)

    # 0. Main Menu -> Hub Room
    assert game.state_manager.current_state == GameState.MAIN_MENU
    game._handle_keydown(pygame.K_RETURN)
    assert game.state_manager.current_state == GameState.HUB_ROOM

    # Start run from Hub Room
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

    # 2. Pause -> Quit Run (Return to Hub Room) requires confirmation, then transitions to HUB_ROOM
    game._handle_keydown(pygame.K_ESCAPE)
    assert game.state_manager.current_state == GameState.PAUSED
    game._handle_keydown(pygame.K_DOWN)  # Select Option 1: Quit Run (Return to Hub Room)
    game._handle_keydown(pygame.K_RETURN)  # Opens confirmation prompt
    assert game.state_manager.current_state == GameState.PAUSED
    assert game.pause_menu.confirming_quit is True
    assert game.run_manager.is_run_active is True

    # Confirm Quit Run -> Hub Room
    game._handle_keydown(pygame.K_RETURN)
    assert game.state_manager.current_state == GameState.HUB_ROOM
    assert game.run_manager.is_run_active is False
    assert game.run_manager.run_outcome == "aborted"

    # 3. Start a new run and test Game Over -> Hub Room flow
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

    # Pressing Enter on Game Over transitions to Hub Room
    game._handle_keydown(pygame.K_RETURN)
    assert game.state_manager.current_state == GameState.HUB_ROOM

    # 4. Final Treasure Room -> Hub Room flow
    game.state_manager.change_state(GameState.TREASURE_ROOM)
    game._handle_keydown(pygame.K_f)  # Claim Grand Chest
    assert game.run_manager.treasure_collected is True
    game._handle_keydown(pygame.K_RETURN)  # Proceed from Treasure Room -> Hub Room
    assert game.state_manager.current_state == GameState.HUB_ROOM
    pygame.quit()


def test_stage_portal_after_boss_and_no_duplicate_portals_or_rewards(tmp_path: Path) -> None:
    """Verify Boss defeat spawns a single StagePortal, does not auto-advance without [F],
    prevents duplicate rewards/portals on repeated events, and advances Stage 1->2->3->Treasure.
    """
    save_sys = SaveSystem(
        save_path=tmp_path / "profile.save.json",
        backup_path=tmp_path / "profile.save.bak",
    )
    prog = ProgressionManager(save_sys)
    run_mgr = RunManager(prog)
    run_mgr.start_new_run(character_id="warrior", seed=24680)

    for stage_idx in (1, 2, 3):
        assert run_mgr.current_stage_index == stage_idx
        for sub_idx in range(1, 6):
            assert run_mgr.current_substage_index == sub_idx
            for e in run_mgr.enemies:
                e.alive = False
            assert run_mgr.shrine_system is not None
            assert run_mgr.player is not None
            wx, wy = run_mgr.shrine_system.shrines[0].world_pos
            run_mgr.player.x, run_mgr.player.y = wx, wy
            ok, _ = run_mgr.try_activate_shrine()
            assert ok is True

        assert run_mgr.in_boss_room is True
        assert run_mgr.boss is not None
        assert run_mgr.portal is None

        # Defeat Boss: must spawn portal in boss room, NOT auto-advance stage
        gold_before = run_mgr.run_gold_earned
        crystals_before = run_mgr.run_crystals_earned
        run_mgr.boss.alive = False
        run_mgr.handle_boss_defeated()

        assert run_mgr.current_stage_index == stage_idx
        assert run_mgr.in_boss_room is True
        assert run_mgr.portal is not None
        first_portal = run_mgr.portal
        gold_after_first = run_mgr.run_gold_earned
        crystals_after_first = run_mgr.run_crystals_earned
        assert gold_after_first > gold_before
        assert crystals_after_first > crystals_before

        # Repeated calls to handle_boss_defeated() must NOT duplicate rewards or replace portal
        run_mgr.handle_boss_defeated()
        run_mgr.handle_boss_defeated()
        assert run_mgr.portal is first_portal
        assert run_mgr.run_gold_earned == gold_after_first
        assert run_mgr.run_crystals_earned == crystals_after_first

        # Player far from portal cannot use it yet
        assert run_mgr.player is not None
        run_mgr.player.x = 0.0
        run_mgr.player.y = 0.0
        used, _ = run_mgr.try_use_stage_portal()
        assert used is False
        assert run_mgr.current_stage_index == stage_idx

        # Move player to Portal and press [F] (try_use_stage_portal)
        px, py = run_mgr.portal.world_pos
        run_mgr.player.x, run_mgr.player.y = px, py
        used, next_state = run_mgr.try_use_stage_portal()
        assert used is True
        if stage_idx < 3:
            assert next_state == "gameplay"
            assert run_mgr.current_stage_index == stage_idx + 1
            assert run_mgr.current_substage_index == 1
            assert run_mgr.in_boss_room is False
            assert run_mgr.portal is None
        else:
            assert next_state == "treasure_room"


def test_shrine_constants_revision_2_0_audit(tmp_path: Path) -> None:
    """Verify Revision 2.0 Shrine and Substage constants (5 Substages/Stage, 1 Shrine/Substage,
    5 Shrines/Stage, 15 Shrines/Run) are enforced throughout RunManager and ShrineSystem.
    """
    assert TOTAL_STAGES_PER_RUN == 3
    assert SUBSTAGES_PER_STAGE == 5
    assert SHRINES_PER_SUBSTAGE == 1
    assert REQUIRED_SHRINES_PER_STAGE_V2 == 5
    assert TOTAL_SUBSTAGES_PER_RUN == 15
    assert TOTAL_SHRINES_PER_RUN == 15

    save_sys = SaveSystem(
        save_path=tmp_path / "profile.save.json",
        backup_path=tmp_path / "profile.save.bak",
    )
    run_mgr = RunManager(ProgressionManager(save_sys))
    run_mgr.start_new_run(character_id="warrior", seed=55555)
    assert run_mgr.shrine_system is not None
    assert run_mgr.shrine_system.required_count == 1
    assert len(run_mgr.shrine_system.shrines) == 1


def test_room_ownership_corridor_and_boss_arena_single_init(tmp_path: Path) -> None:
    """Verify Player.current_room_id updates across rooms and corridors, projectiles/hitboxes
    clear on transitions, and Boss Arena has isolated room ownership and single initialization.
    """
    save_sys = SaveSystem(
        save_path=tmp_path / "profile.save.json",
        backup_path=tmp_path / "profile.save.bak",
    )
    run_mgr = RunManager(ProgressionManager(save_sys))
    run_mgr.start_new_run(character_id="warrior", seed=31415)
    assert run_mgr.player is not None
    assert run_mgr.dungeon is not None

    # Player starts in Entrance Room
    entrance = run_mgr.dungeon.entrance_room
    assert run_mgr.player.current_room_id == entrance.room_id

    # Move player to a second room and verify sync_player_room_ownership updates current_room_id
    other_room = next(r for r in run_mgr.dungeon.rooms if r.room_id != entrance.room_id)
    ox, oy = other_room.center
    run_mgr.player.x = ox * TILE_SIZE + TILE_SIZE * 0.5
    run_mgr.player.y = oy * TILE_SIZE + TILE_SIZE * 0.5
    assert run_mgr.sync_player_room_ownership() == other_room.room_id

    # Move player to a corridor tile outside all rooms -> current_room_id becomes None
    corr_tile = next(
        t
        for corr in run_mgr.dungeon.corridors
        for t in corr.tiles
        if run_mgr.dungeon.get_room_at_tile(*t) is None
    )
    run_mgr.player.x = corr_tile[0] * TILE_SIZE + TILE_SIZE * 0.5
    run_mgr.player.y = corr_tile[1] * TILE_SIZE + TILE_SIZE * 0.5
    assert run_mgr.sync_player_room_ownership() is None

    # While player is in corridor (current_room_id is None), enemies in rooms must NOT chase/attack
    for enemy in run_mgr.enemies:
        enemy.update(
            0.1,
            run_mgr.player,
            run_mgr.dungeon.tilemap,
            run_mgr.combat_system,
            run_mgr._stage_rng,
        )
        assert enemy.state in (EnemyState.IDLE, EnemyState.PATROL)

    # Spawn projectiles & melee arcs, then transition substage -> verify combat_system is cleared
    run_mgr.combat_system.spawn_player_basic_attack(run_mgr.player, 1.0, 0.0)
    assert len(run_mgr.combat_system.melee_arcs) > 0
    for e in run_mgr.enemies:
        e.alive = False
    assert run_mgr.shrine_system is not None
    sx, sy = run_mgr.shrine_system.shrines[0].world_pos
    run_mgr.player.x, run_mgr.player.y = sx, sy
    ok, _ = run_mgr.try_activate_shrine()
    assert ok is True
    assert len(run_mgr.combat_system.melee_arcs) == 0
    assert len(run_mgr.combat_system.projectiles) == 0

    # Advance to Shrine 5 and verify Boss Arena single initialization & room ownership
    for _ in range(2, 6):
        for e in run_mgr.enemies:
            e.alive = False
        assert run_mgr.shrine_system is not None
        sx, sy = run_mgr.shrine_system.shrines[0].world_pos
        run_mgr.player.x, run_mgr.player.y = sx, sy
        run_mgr.try_activate_shrine()

    assert run_mgr.in_boss_room is True
    assert run_mgr.boss is not None
    assert run_mgr.dungeon.entrance_room.room_id == 0
    assert run_mgr.dungeon.boss_room.room_id == 1
    assert run_mgr.player.current_room_id == 0
    assert run_mgr.boss.room_id == 1

    # Boss in room 1 does not engage while player is in entrance room 0
    run_mgr.boss.update(
        0.1,
        run_mgr.player,
        run_mgr.dungeon.tilemap,
        run_mgr.combat_system,
        run_mgr._stage_rng,
    )
    assert run_mgr.boss.engaged is False

    # Calling _load_boss_arena(1) again must be a no-op (single initialization per stage)
    first_boss_instance = run_mgr.boss
    run_mgr._load_boss_arena(1)
    assert run_mgr.boss is first_boss_instance


def test_deterministic_generation_and_content_rng_isolation(tmp_path: Path) -> None:
    """Prove the same Run Seed produces identical biome order, graph, room geometry,
    Entrance/Shrine positions, mandatory enemy rooms, and optional room types, and that
    altering Room Contents RNG does NOT alter Dungeon Layout.
    """
    save1 = SaveSystem(tmp_path / "p1.json", tmp_path / "p1.bak")
    save2 = SaveSystem(tmp_path / "p2.json", tmp_path / "p2.bak")
    rm1 = RunManager(ProgressionManager(save1))
    rm2 = RunManager(ProgressionManager(save2))
    rm1.start_new_run("warrior", seed=909090)
    rm2.start_new_run("warrior", seed=909090)

    assert rm1.stage_biomes == rm2.stage_biomes

    gen = DungeonGenerator("enchanted_forest")
    d1 = gen.generate_substage(run_seed=909090, stage_index=1, substage_index=3)
    d2 = gen.generate_substage(run_seed=909090, stage_index=1, substage_index=3)

    assert d1.graph.edges == d2.graph.edges
    assert [(r.room_id, r.x, r.y, r.width, r.height, r.room_type, r.is_mandatory) for r in d1.rooms] == [
        (r.room_id, r.x, r.y, r.width, r.height, r.room_type, r.is_mandatory) for r in d2.rooms
    ]
    assert d1.entrance_room.center == d2.entrance_room.center
    assert d1.shrine_positions == d2.shrine_positions
    assert d1.mandatory_path_room_ids == d2.mandatory_path_room_ids

    # Now override room_content_rng with a completely different RNG state and verify
    # Dungeon Layout (room coordinates/sizes, graph edges, entrance, shrine, mandatory path, tilemap)
    # is 100% unchanged!
    perturbed_content_rng = random.Random(123456789)
    for _ in range(50):
        perturbed_content_rng.random()
    d_perturbed = gen.generate_substage(
        run_seed=909090,
        stage_index=1,
        substage_index=3,
        content_rng_override=perturbed_content_rng,
    )

    assert d_perturbed.graph.edges == d1.graph.edges
    assert [(r.room_id, r.x, r.y, r.width, r.height) for r in d_perturbed.rooms] == [
        (r.room_id, r.x, r.y, r.width, r.height) for r in d1.rooms
    ]
    assert d_perturbed.entrance_room.center == d1.entrance_room.center
    assert d_perturbed.shrine_positions == d1.shrine_positions
    assert d_perturbed.mandatory_path_room_ids == d1.mandatory_path_room_ids
    assert d_perturbed.tilemap.grid == d1.tilemap.grid

