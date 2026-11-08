"""Controllable player entity with Chibi 32x32 spritesheet and AnimationController."""

from __future__ import annotations

import math
import pygame

from characters.character_data import CharacterStats
from combat.damage import DamagePacket
from config.settings import SPRITE_SIZE_CHARACTER, TILE_SIZE
from systems.animation import AnimationController, AnimationState, Direction
from systems.asset_manager import AssetManager
from systems.collision import move_with_tile_collision
from world.tilemap import TileMap


class Player:
    """Top-down controllable player character with 4-direction 8-frame animation."""

    def __init__(
        self,
        x: float,
        y: float,
        stats: CharacterStats,
        skill_1_unlocked: bool = False,
        skill_2_unlocked: bool = False,
    ) -> None:
        self.x: float = x
        self.y: float = y
        self.stats: CharacterStats = stats
        self.max_hp: int = stats.max_hp
        self.hp: int = stats.max_hp
        self.alive: bool = True

        # Collision dimensions (preserved strictly independent of 32x32 sprite size)
        self.half_size: int = 6
        self.radius: float = 6.5
        self.visual_size: tuple[int, int] = SPRITE_SIZE_CHARACTER

        self.facing_x: float = 0.0
        self.facing_y: float = 1.0

        self.skill_1_unlocked: bool = skill_1_unlocked
        self.skill_2_unlocked: bool = skill_2_unlocked

        # Cooldown & state timers
        self.attack_cooldown_timer: float = 0.0
        self.skill_1_cooldown_timer: float = 0.0
        self.skill_2_cooldown_timer: float = 0.0
        self.dash_cooldown_timer: float = 0.0
        self.dash_active_timer: float = 0.0
        self.invulnerable_timer: float = 0.0
        self.hit_flash_timer: float = 0.0

        self.dash_dir_x: float = 1.0
        self.dash_dir_y: float = 0.0
        self.knockback_vx: float = 0.0
        self.knockback_vy: float = 0.0
        self.current_room_id: int | None = None

        # AnimationController & combat event synchronization log
        self.anim_controller: AnimationController = (
            AssetManager.get_instance().create_character_animation_controller(
                stats.character_id
            )
        )
        self.last_animation_events: list[str] = []

    @property
    def tile_pos(self) -> tuple[int, int]:
        """Return the current (tx, ty) tile coordinates of the player."""
        return (int(self.x // TILE_SIZE), int(self.y // TILE_SIZE))

    @property
    def foot_y(self) -> float:
        """Return world Y coordinate of the player's feet for Y-sorting."""
        return self.y + float(self.half_size)

    @property
    def is_invulnerable(self) -> bool:
        """Return True if the player currently has invulnerability frames (dodge or hit)."""
        return self.invulnerable_timer > 0.0 or self.dash_active_timer > 0.0

    def update_aim(self, world_mouse_x: float, world_mouse_y: float) -> None:
        """Update normalized directional aim vector toward world mouse cursor."""
        if not self.alive:
            return
        dx = world_mouse_x - self.x
        dy = world_mouse_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1e-4:
            self.facing_x = dx / dist
            self.facing_y = dy / dist
            self.anim_controller.set_direction_from_vector(self.facing_x, self.facing_y)

    def try_dash(self, move_dx: float, move_dy: float) -> bool:
        """Initiate a dodge-dash with invulnerability frames if off cooldown."""
        if not self.alive or self.dash_cooldown_timer > 0.0 or self.dash_active_timer > 0.0:
            return False

        mag = math.hypot(move_dx, move_dy)
        if mag > 1e-4:
            self.dash_dir_x = move_dx / mag
            self.dash_dir_y = move_dy / mag
        else:
            self.dash_dir_x = self.facing_x
            self.dash_dir_y = self.facing_y

        self.dash_active_timer = self.stats.dash_duration
        self.dash_cooldown_timer = self.stats.dash_cooldown
        self.invulnerable_timer = max(self.invulnerable_timer, self.stats.dash_duration + 0.08)
        self.anim_controller.set_direction_from_vector(self.dash_dir_x, self.dash_dir_y)
        self.anim_controller.play(AnimationState.WALK)
        return True

    def can_basic_attack(self) -> bool:
        """Return True if the player can perform a basic attack."""
        return self.alive and self.attack_cooldown_timer <= 0.0

    def trigger_basic_attack(self) -> bool:
        """Consume basic attack cooldown and trigger 8-frame Attack animation."""
        if not self.can_basic_attack():
            return False
        self.attack_cooldown_timer = self.stats.attack_cooldown
        self.anim_controller.play(
            AnimationState.ATTACK,
            direction=Direction.from_vector(self.facing_x, self.facing_y),
            restart_if_same=True,
        )
        return True

    def can_use_skill(self, slot: int) -> bool:
        """Return True if the specified skill slot (1 or 2) is unlocked and off cooldown."""
        if not self.alive:
            return False
        if slot == 1:
            return self.skill_1_unlocked and self.skill_1_cooldown_timer <= 0.0
        if slot == 2:
            return self.skill_2_unlocked and self.skill_2_cooldown_timer <= 0.0
        return False

    def trigger_skill(self, slot: int) -> bool:
        """Start cooldown and play Skill 1 or Skill 2 animation."""
        if not self.can_use_skill(slot):
            return False
        if slot == 1:
            self.skill_1_cooldown_timer = self.stats.skill_1.cooldown
            self.anim_controller.play(
                AnimationState.SKILL_1,
                direction=Direction.from_vector(self.facing_x, self.facing_y),
                restart_if_same=True,
            )
        else:
            self.skill_2_cooldown_timer = self.stats.skill_2.cooldown
            self.anim_controller.play(
                AnimationState.SKILL_2,
                direction=Direction.from_vector(self.facing_x, self.facing_y),
                restart_if_same=True,
            )
        return True

    def take_damage(self, packet: DamagePacket) -> bool:
        """Apply incoming damage and knockback if not invulnerable. Returns True if hit."""
        if not self.alive or self.is_invulnerable:
            return False

        self.hp = max(0, self.hp - packet.amount)
        self.invulnerable_timer = 0.45
        self.hit_flash_timer = 0.18
        kvx, kvy = packet.compute_knockback_vector(self.x, self.y, knockback_resistance=0.15)
        self.knockback_vx = kvx
        self.knockback_vy = kvy

        if self.hp <= 0:
            self.alive = False
            self.anim_controller.play(AnimationState.DEATH, restart_if_same=True)
        else:
            self.anim_controller.play(AnimationState.HURT, restart_if_same=True)
        return True

    def heal(self, amount: int) -> None:
        """Restore player health up to max_hp."""
        if self.alive:
            self.hp = min(self.max_hp, self.hp + amount)

    def update(
        self,
        dt: float,
        move_dx: float,
        move_dy: float,
        tilemap: TileMap,
    ) -> None:
        """Update timers, dash velocity, movement input, wall collisions, and animations."""
        if self.attack_cooldown_timer > 0.0:
            self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        if self.skill_1_cooldown_timer > 0.0:
            self.skill_1_cooldown_timer = max(0.0, self.skill_1_cooldown_timer - dt)
        if self.skill_2_cooldown_timer > 0.0:
            self.skill_2_cooldown_timer = max(0.0, self.skill_2_cooldown_timer - dt)
        if self.dash_cooldown_timer > 0.0:
            self.dash_cooldown_timer = max(0.0, self.dash_cooldown_timer - dt)
        if self.invulnerable_timer > 0.0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        if self.hit_flash_timer > 0.0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

        if not self.alive:
            self.anim_controller.play(AnimationState.DEATH)
            self.last_animation_events = self.anim_controller.update(dt)
            return

        is_moving = False
        if self.dash_active_timer > 0.0:
            self.dash_active_timer = max(0.0, self.dash_active_timer - dt)
            vx = self.dash_dir_x * self.stats.dash_speed
            vy = self.dash_dir_y * self.stats.dash_speed
            is_moving = True
        else:
            mag = math.hypot(move_dx, move_dy)
            if mag > 1e-4:
                nx = move_dx / mag
                ny = move_dy / mag
                is_moving = True
            else:
                nx, ny = 0.0, 0.0
            vx = nx * self.stats.move_speed + self.knockback_vx
            vy = ny * self.stats.move_speed + self.knockback_vy

        # Transition between WALK and IDLE when not locked in a higher-priority one-shot clip
        if is_moving:
            self.anim_controller.play(AnimationState.WALK)
        else:
            self.anim_controller.play(AnimationState.IDLE)

        self.last_animation_events = self.anim_controller.update(dt)

        # Exponential decay of knockback velocity
        decay = max(0.0, 1.0 - 10.0 * dt)
        self.knockback_vx *= decay
        self.knockback_vy *= decay

        self.x, self.y = move_with_tile_collision(
            self.x,
            self.y,
            vx,
            vy,
            dt,
            self.half_size,
            tilemap,
        )

    def render(self, surface: pygame.Surface, camera_offset: tuple[int, int]) -> None:
        """Render the 32x32 Chibi Pixel-Art sprite anchored by foot_y."""
        cam_x, cam_y = camera_offset
        sx = int(round(self.x - cam_x))
        foot_screen_y = int(round(self.foot_y - cam_y))

        # Ground shadow beneath feet
        pygame.draw.ellipse(
            surface,
            (10, 8, 15),
            pygame.Rect(sx - 7, foot_screen_y - 3, 14, 5),
        )

        frame_surf = self.anim_controller.get_current_frame()
        fw, fh = frame_surf.get_size()
        # Anchor 32x32 sprite so the chibi boots at y=30 align with foot_screen_y
        draw_x = sx - fw // 2
        draw_y = foot_screen_y - (fh - 2)
        surface.blit(frame_surf, (draw_x, draw_y))
