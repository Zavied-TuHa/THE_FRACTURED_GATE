"""Reusable Enemy base class and AI state machine for melee, ranged, fast, and elite foes."""

from __future__ import annotations

from enum import Enum
import math
import random
from typing import TYPE_CHECKING
import pygame

from combat.abilities import MeleeAttackArc
from combat.damage import DamagePacket
from config.balance import ENEMY_CONFIGS, ENEMY_DROP_TABLE
from config.settings import (
    COLOR_ENEMY_ELITE,
    COLOR_ENEMY_FAST,
    COLOR_ENEMY_MELEE,
    COLOR_ENEMY_RANGED,
)
from entities.projectile import Projectile
from systems.collision import move_with_tile_collision

if TYPE_CHECKING:
    from combat.combat_system import CombatSystem
    from entities.player import Player
    from world.tilemap import TileMap


class EnemyState(Enum):
    """Finite state machine states for enemy AI."""

    DORMANT = "dormant"
    IDLE = "idle"
    PATROL = "patrol"
    CHASE = "chase"
    ATTACK = "attack"
    HURT = "hurt"
    DEAD = "dead"


ARCHETYPE_COLORS: dict[str, tuple[int, int, int]] = {
    "melee": COLOR_ENEMY_MELEE,
    "ranged": COLOR_ENEMY_RANGED,
    "fast": COLOR_ENEMY_FAST,
    "elite": COLOR_ENEMY_ELITE,
    "mini_boss": (220, 80, 120),
}


class Enemy:
    """Reusable enemy entity supporting multiple archetypes and AI states."""

    _next_id: int = 1

    def __init__(
        self,
        x: float,
        y: float,
        archetype: str = "melee",
        room_id: int = 0,
        room_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        self.entity_id: int = Enemy._next_id
        Enemy._next_id += 1

        self.x: float = x
        self.y: float = y
        self.archetype: str = archetype if archetype in ENEMY_CONFIGS else "melee"
        self.room_id: int = room_id
        self.room_bounds: tuple[float, float, float, float] | None = room_bounds

        cfg = ENEMY_CONFIGS[self.archetype]
        self.name: str = str(cfg["name"])
        self.max_hp: int = int(cfg["max_hp"])
        self.hp: int = self.max_hp
        self.move_speed: float = float(cfg["move_speed"])
        self.damage: int = int(cfg["damage"])
        self.attack_range: float = float(cfg["attack_range"])
        self.detection_range: float = float(cfg["detection_range"])
        self.attack_cooldown: float = float(cfg["attack_cooldown"])
        self.projectile_speed: float = float(cfg.get("projectile_speed", 135.0))
        self.knockback_resist: float = float(cfg.get("knockback_resist", 0.0))
        self.size: int = int(cfg.get("size", 12))
        self.half_size: int = max(4, self.size // 2)
        self.radius: float = float(self.half_size)

        drops = ENEMY_DROP_TABLE.get(self.archetype, {"gold": 5, "crystals": 0})
        self.gold_drop: int = int(drops["gold"])
        self.crystal_drop: int = int(drops["crystals"])

        self.color: tuple[int, int, int] = ARCHETYPE_COLORS.get(
            self.archetype, COLOR_ENEMY_MELEE
        )

        self.state: EnemyState = EnemyState.IDLE
        self.alive: bool = True

        self.attack_timer: float = 0.0
        self.hit_flash_timer: float = 0.0
        self.patrol_timer: float = 1.2
        self.patrol_dir_x: float = 0.0
        self.patrol_dir_y: float = 0.0
        self.knockback_vx: float = 0.0
        self.knockback_vy: float = 0.0

    @property
    def foot_y(self) -> float:
        """Return world Y coordinate of the enemy's feet for Y-sorting."""
        return self.y + float(self.half_size)

    def take_damage(self, packet: DamagePacket) -> bool:
        """Apply damage and knockback to this enemy. Return True if this hit killed it."""
        if not self.alive:
            return False

        self.hp = max(0, self.hp - packet.amount)
        self.hit_flash_timer = 0.14
        kvx, kvy = packet.compute_knockback_vector(
            self.x, self.y, knockback_resistance=self.knockback_resist
        )
        self.knockback_vx = kvx
        self.knockback_vy = kvy

        if self.hp <= 0:
            self.alive = False
            self.state = EnemyState.DEAD
            return True

        self.state = EnemyState.CHASE
        return False

    def update(
        self,
        dt: float,
        player: Player,
        tilemap: TileMap,
        combat_system: CombatSystem,
        rng: random.Random,
    ) -> None:
        """Execute AI state transitions, movement, and attacks."""
        if not self.alive or self.state == EnemyState.DORMANT:
            return

        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt)
        if self.hit_flash_timer > 0.0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)

        dx = player.x - self.x
        dy = player.y - self.y
        dist_to_player = math.hypot(dx, dy)
        same_room = (
            player.current_room_id is not None
            and player.current_room_id == self.room_id
        )

        # AI state selection (strictly isolated by room ownership)
        if same_room and player.alive and dist_to_player <= self.attack_range:
            self.state = EnemyState.ATTACK
        elif same_room and player.alive and dist_to_player <= self.detection_range:
            self.state = EnemyState.CHASE
        else:
            if self.state in (EnemyState.CHASE, EnemyState.ATTACK):
                self.state = EnemyState.IDLE
                self.patrol_timer = 0.5
            self.patrol_timer -= dt
            if self.patrol_timer <= 0.0:
                if self.state == EnemyState.IDLE:
                    self.state = EnemyState.PATROL
                    ang = rng.uniform(0.0, math.pi * 2.0)
                    self.patrol_dir_x = math.cos(ang)
                    self.patrol_dir_y = math.sin(ang)
                    self.patrol_timer = rng.uniform(0.8, 1.8)
                else:
                    self.state = EnemyState.IDLE
                    self.patrol_dir_x = 0.0
                    self.patrol_dir_y = 0.0
                    self.patrol_timer = rng.uniform(0.6, 1.4)

        move_vx = 0.0
        move_vy = 0.0

        if self.state == EnemyState.PATROL:
            move_vx = self.patrol_dir_x * (self.move_speed * 0.45)
            move_vy = self.patrol_dir_y * (self.move_speed * 0.45)
        elif self.state == EnemyState.CHASE and dist_to_player > 1e-4:
            nx = dx / dist_to_player
            ny = dy / dist_to_player
            move_vx = nx * self.move_speed
            move_vy = ny * self.move_speed
        elif self.state == EnemyState.ATTACK and dist_to_player > 1e-4:
            nx = dx / dist_to_player
            ny = dy / dist_to_player
            if self.archetype == "ranged" and dist_to_player < self.attack_range * 0.45:
                move_vx = -nx * (self.move_speed * 0.5)
                move_vy = -ny * (self.move_speed * 0.5)
            if self.attack_timer <= 0.0:
                self._perform_attack(nx, ny, combat_system)
                self.attack_timer = self.attack_cooldown

        total_vx = move_vx + self.knockback_vx
        total_vy = move_vy + self.knockback_vy

        decay = max(0.0, 1.0 - 10.0 * dt)
        self.knockback_vx *= decay
        self.knockback_vy *= decay

        self.x, self.y = move_with_tile_collision(
            self.x,
            self.y,
            total_vx,
            total_vy,
            dt,
            self.half_size,
            tilemap,
        )

        # Keep enemy strictly inside its assigned room bounds
        if self.room_bounds is not None:
            min_x, min_y, max_x, max_y = self.room_bounds
            pad = float(self.half_size)
            if max_x - min_x > pad * 2.0:
                self.x = max(min_x + pad, min(max_x - pad, self.x))
            if max_y - min_y > pad * 2.0:
                self.y = max(min_y + pad, min(max_y - pad, self.y))

    def _perform_attack(
        self,
        dir_x: float,
        dir_y: float,
        combat_system: CombatSystem,
    ) -> None:
        """Spawn enemy melee attack arc or ranged projectile."""
        if self.archetype == "ranged":
            combat_system.projectiles.append(
                Projectile(
                    x=self.x + dir_x * (self.radius + 3.0),
                    y=self.y + dir_y * (self.radius + 3.0),
                    dir_x=dir_x,
                    dir_y=dir_y,
                    speed=self.projectile_speed,
                    damage=self.damage,
                    max_distance=self.attack_range + 35.0,
                    owner_is_player=False,
                    color=(210, 95, 245),
                    room_id=self.room_id,
                    room_bounds=self.room_bounds,
                )
            )
        else:
            combat_system.melee_arcs.append(
                MeleeAttackArc(
                    owner_is_player=False,
                    origin_x=self.x,
                    origin_y=self.y,
                    dir_x=dir_x,
                    dir_y=dir_y,
                    radius=self.attack_range + 6.0,
                    arc_angle_rad=math.radians(95),
                    damage=self.damage,
                    knockback_force=95.0,
                    duration=0.14,
                    color=(235, 80, 85),
                    room_id=self.room_id,
                )
            )

    def render(self, surface: pygame.Surface, camera_offset: tuple[int, int]) -> None:
        """Render the enemy sprite and mini health bar above it."""
        if not self.alive:
            return

        cam_x, cam_y = camera_offset
        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))

        draw_color = (255, 255, 255) if self.hit_flash_timer > 0.0 else self.color
        body_rect = pygame.Rect(
            sx - self.half_size,
            sy - self.half_size,
            self.size,
            self.size,
        )
        pygame.draw.rect(surface, draw_color, body_rect)
        pygame.draw.rect(surface, (20, 14, 24), body_rect, 1)

        # Glowing eyes
        pygame.draw.rect(surface, (255, 220, 90), pygame.Rect(sx - 3, sy - 2, 2, 2))
        pygame.draw.rect(surface, (255, 220, 90), pygame.Rect(sx + 1, sy - 2, 2, 2))

        # Mini health bar if damaged
        if self.hp < self.max_hp:
            bar_w = max(12, self.size + 2)
            bar_x = sx - bar_w // 2
            bar_y = sy - self.half_size - 5
            ratio = max(0.0, self.hp / max(1, self.max_hp))
            pygame.draw.rect(surface, (45, 18, 24), pygame.Rect(bar_x, bar_y, bar_w, 3))
            pygame.draw.rect(
                surface,
                (210, 45, 55),
                pygame.Rect(bar_x, bar_y, int(bar_w * ratio), 3),
            )
