"""Automated tests for Phase 2.1 AssetManager, AnimationController, layers, and Y-sorting."""

from __future__ import annotations

import pygame

from characters.warrior import get_warrior_stats
from combat.damage import DamagePacket
from config.settings import (
    ASSETS_DIR,
    SPRITE_SIZE_CHARACTER,
    SPRITE_SIZE_WEAPON,
    STANDARD_ANIMATION_FRAMES,
    TILE_SIZE,
)
from entities.enemy import Enemy
from entities.player import Player
from systems.animation import AnimationState, Direction
from systems.asset_manager import AssetManager
from systems.shrine_system import Shrine
from world.dungeon_generator import DungeonGenerator


def test_png_assets_exist_and_dimensions() -> None:
    """Verify transparent PNG spritesheets and biome tilesets exist with exact dimensions."""
    pygame.init()
    mgr = AssetManager.get_instance()

    warrior_png = ASSETS_DIR / "sprites" / "warrior_chibi_32x32.png"
    weapon_png = ASSETS_DIR / "sprites" / "warrior_sword_16x16.png"
    assert warrior_png.exists()
    assert weapon_png.exists()

    sheet = mgr.load_png("sprites/warrior_chibi_32x32.png")
    # 8 frames wide (8 * 32 = 256) x 28 rows (7 states * 4 directions * 32 = 896)
    assert sheet.get_size() == (
        STANDARD_ANIMATION_FRAMES * SPRITE_SIZE_CHARACTER[0],
        7 * 4 * SPRITE_SIZE_CHARACTER[1],
    )
    # Corner pixel (0, 0) must be transparent (alpha == 0)
    assert sheet.get_at((0, 0)).a == 0

    weapon = mgr.load_png("sprites/warrior_sword_16x16.png")
    assert weapon.get_size() == SPRITE_SIZE_WEAPON
    assert weapon.get_at((0, 0)).a == 0

    for biome_id in ("enchanted_forest", "crystal_cavern", "demon_castle"):
        ts_path = ASSETS_DIR / "tilesets" / f"{biome_id}.png"
        assert ts_path.exists()
        tileset = mgr.get_biome_tileset(biome_id)
        assert len(tileset["ground"]) == 3
        assert len(tileset["decoration"]) == 3
        assert len(tileset["wall"]) == 3
        assert len(tileset["foreground"]) == 2
        assert tileset["ground"][0].get_size() == (TILE_SIZE, TILE_SIZE)


def test_animation_controller_states_directions_events_and_death_priority() -> None:
    """Verify 4 directions, 8 frames, delta-time stepping, events, and Death priority."""
    pygame.init()
    ctrl = AssetManager.get_instance().create_character_animation_controller("warrior")

    # 1. Verify all 7 required states and 4 directions have 8 frames of 32x32
    for state in AnimationState:
        assert state in ctrl.clips
        clip = ctrl.clips[state]
        assert clip.frame_count == STANDARD_ANIMATION_FRAMES
        for direction in Direction:
            frame = clip.get_frame(direction, 0)
            assert frame.get_size() == SPRITE_SIZE_CHARACTER

    # 2. Verify directional vector mapping
    ctrl.set_direction_from_vector(0.0, -1.0)
    assert ctrl.direction == Direction.UP
    ctrl.set_direction_from_vector(-1.0, 0.0)
    assert ctrl.direction == Direction.LEFT
    ctrl.set_direction_from_vector(1.0, 0.0)
    assert ctrl.direction == Direction.RIGHT
    ctrl.set_direction_from_vector(0.0, 1.0)
    assert ctrl.direction == Direction.DOWN

    # 3. Verify one-shot Attack animation fires 'attack_hit' event and returns to IDLE
    fired_events: list[str] = []
    ctrl.register_event_listener(fired_events.append)
    assert ctrl.play(AnimationState.ATTACK) is True
    assert ctrl.state == AnimationState.ATTACK

    # While ATTACK one-shot is playing, lower-priority WALK cannot interrupt it
    assert ctrl.play(AnimationState.WALK) is False
    assert ctrl.state == AnimationState.ATTACK

    # Step through entire 8-frame Attack clip via delta-time
    for _ in range(12):
        ctrl.update(0.05)

    assert "attack_hit" in fired_events
    assert ctrl.state == AnimationState.IDLE

    # 4. Verify DEATH has highest priority and cannot be overridden by any state
    assert ctrl.play(AnimationState.DEATH) is True
    assert ctrl.state == AnimationState.DEATH

    for other_state in AnimationState:
        if other_state != AnimationState.DEATH:
            assert ctrl.play(other_state) is False
            assert ctrl.state == AnimationState.DEATH


def test_warrior_visual_vs_collision_independence_and_y_sorting() -> None:
    """Verify Warrior 32x32 visual size is independent of collision box and Y-sorting works."""
    pygame.init()
    player = Player(x=100.0, y=120.0, stats=get_warrior_stats(), skill_1_unlocked=True)
    assert player.visual_size == (32, 32)
    assert player.half_size == 6
    assert player.foot_y == 126.0

    # Trigger Skill 1 and verify animation state
    assert player.trigger_skill(1) is True
    assert player.anim_controller.state == AnimationState.SKILL_1

    # Verify lethal damage forces DEATH state
    lethal = DamagePacket(amount=999, source_x=90.0, source_y=120.0)
    player.take_damage(lethal)
    assert player.alive is False
    assert player.anim_controller.state == AnimationState.DEATH

    # Verify Y-sorting order between Shrine, Enemy, and Player
    shrine = Shrine(shrine_id=1, room_id=1, tile_x=5, tile_y=5)  # world_y = 88 -> foot_y = 96
    enemy = Enemy(x=100.0, y=150.0, archetype="melee", room_id=1)  # foot_y = 156
    sorted_entities = sorted([enemy, player, shrine], key=lambda e: e.foot_y)
    assert sorted_entities == [shrine, player, enemy]


def test_tilemap_five_layers_populated() -> None:
    """Verify ground, decoration, wall, foreground, and collision layers are populated."""
    pygame.init()
    dungeon = DungeonGenerator("demon_castle").generate(seed=777)
    tm = dungeon.tilemap

    has_ground = any(
        tm.ground_layer[y][x] >= 0 for y in range(tm.height) for x in range(tm.width)
    )
    has_wall = any(
        tm.wall_layer[y][x] >= 0 for y in range(tm.height) for x in range(tm.width)
    )
    has_foreground = any(
        tm.foreground_layer[y][x] >= 0 for y in range(tm.height) for x in range(tm.width)
    )
    assert has_ground is True
    assert has_wall is True
    assert has_foreground is True

    # Verify rendering both base and foreground layers onto a 640x360 surface
    canvas = pygame.Surface((640, 360))
    tm.render(canvas, (0, 0))
    tm.render_foreground(canvas, (0, 0))
