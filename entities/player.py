"""Controllable player entity driven by CharacterStats."""

from __future__ import annotations

import math
import pygame

from characters.character_data import CharacterStats
from combat.damage import DamagePacket
from config.settings import COLOR_PLAYER_DASH, TILE_SIZE
from systems.collision import move_with_tile_collision
from world.tilemap import TileMap


class Player:
    """Top-down controllable player character with combat, skills, and dodge-dash."""

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

        self.half_size: int = 6
        self.radius: float = 6.5

        self.facing_x: float = 1.0
        self.facing_y: float = 0.0

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

    @property
    def tile_pos(self) -> tuple[int, int]:
        """Return the current (tx, ty) tile coordinates of the player."""
        return (int(self.x // TILE_SIZE), int(self.y // TILE_SIZE))

    @property
    def is_invulnerable(self) -> bool:
        """Return True if the player currently has invulnerability frames (dodge or hit)."""
        return self.invulnerable_timer > 0.0 or self.dash_active_timer > 0.0

    def update_aim(self, world_mouse_x: float, world_mouse_y: float) -> None:
        """Update normalized directional aim vector toward world mouse cursor."""
        dx = world_mouse_x - self.x
        dy = world_mouse_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1e-4:
            self.facing_x = dx / dist
            self.facing_y = dy / dist

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
        return True

    def can_basic_attack(self) -> bool:
        """Return True if the player can perform a basic attack."""
        return self.alive and self.attack_cooldown_timer <= 0.0

    def trigger_basic_attack(self) -> bool:
        """Consume basic attack cooldown; return True if triggered."""
        if not self.can_basic_attack():
            return False
        self.attack_cooldown_timer = self.stats.attack_cooldown
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
        """Start cooldown for skill slot 1 or 2 if available."""
        if not self.can_use_skill(slot):
            return False
        if slot == 1:
            self.skill_1_cooldown_timer = self.stats.skill_1.cooldown
        else:
            self.skill_2_cooldown_timer = self.stats.skill_2.cooldown
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
        """Update timers, dash velocity, movement input, and wall collisions."""
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
            return

        if self.dash_active_timer > 0.0:
            self.dash_active_timer = max(0.0, self.dash_active_timer - dt)
            vx = self.dash_dir_x * self.stats.dash_speed
            vy = self.dash_dir_y * self.stats.dash_speed
        else:
            mag = math.hypot(move_dx, move_dy)
            if mag > 1e-4:
                nx = move_dx / mag
                ny = move_dy / mag
            else:
                nx, ny = 0.0, 0.0
            vx = nx * self.stats.move_speed + self.knockback_vx
            vy = ny * self.stats.move_speed + self.knockback_vy

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
        """Render the pixel-art knight/character sprite and aim indicator."""
        cam_x, cam_y = camera_offset
        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))

        # Shadow
        pygame.draw.ellipse(
            surface,
            (12, 10, 16),
            pygame.Rect(sx - 6, sy + 3, 12, 5),
        )

        body_color = self.stats.color
        if self.hit_flash_timer > 0.0:
            body_color = (255, 255, 255)
        elif self.dash_active_timer > 0.0:
            body_color = COLOR_PLAYER_DASH

        body_rect = pygame.Rect(
            sx - self.half_size,
            sy - self.half_size,
            self.half_size * 2,
            self.half_size * 2,
        )
        pygame.draw.rect(surface, body_color, body_rect)
        pygame.draw.rect(surface, (28, 22, 34), body_rect, 1)

        # Visor / eyes toward facing direction
        eye_x = sx + int(round(self.facing_x * 3))
        eye_y = sy - 1 + int(round(self.facing_y * 2))
        pygame.draw.rect(surface, (30, 26, 40), pygame.Rect(eye_x - 2, eye_y - 1, 4, 2))

        # Directional weapon tip indicator
        wx = sx + int(round(self.facing_x * 9))
        wy = sy + int(round(self.facing_y * 9))
        pygame.draw.line(surface, (220, 220, 235), (sx, sy), (wx, wy), 2)
