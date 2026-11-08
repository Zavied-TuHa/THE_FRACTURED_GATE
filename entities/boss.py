"""Stage Boss entity with multi-phase melee and radial projectile patterns."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING
import pygame

from combat.abilities import MeleeAttackArc
from config.settings import COLOR_BOSS
from entities.enemy import Enemy, EnemyState
from entities.projectile import Projectile

if TYPE_CHECKING:
    from combat.combat_system import CombatSystem
    from entities.player import Player
    from world.tilemap import TileMap


class Boss(Enemy):
    """Stage Boss featuring heavy melee cleaves and radial projectile novas."""

    def __init__(
        self,
        x: float,
        y: float,
        room_id: int,
        boss_name: str = "Malakor, Sovereign of the Gate",
        stage_index: int = 1,
        room_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        super().__init__(
            x=x,
            y=y,
            archetype="boss",
            room_id=room_id,
            room_bounds=room_bounds,
        )
        self.name = boss_name
        # Scale boss health and damage slightly with stage index (1..3)
        scale = 1.0 + 0.22 * (stage_index - 1)
        self.max_hp = int(round(self.max_hp * scale))
        self.hp = self.max_hp
        self.damage = int(round(self.damage * (1.0 + 0.12 * (stage_index - 1))))
        self.color = COLOR_BOSS
        self.nova_cooldown_timer: float = 3.5
        self.engaged: bool = False

    def update(
        self,
        dt: float,
        player: Player,
        tilemap: TileMap,
        combat_system: CombatSystem,
        rng: random.Random,
    ) -> None:
        """Update boss AI, radial nova pattern, and base movement/attacks."""
        if not self.alive or self.state == EnemyState.DORMANT:
            return

        same_room = (
            player.current_room_id is None or player.current_room_id == self.room_id
        )
        dist = math.hypot(player.x - self.x, player.y - self.y)
        if same_room and (dist <= self.detection_range or self.hp < self.max_hp):
            self.engaged = True

        self.nova_cooldown_timer = max(0.0, self.nova_cooldown_timer - dt)
        if same_room and self.engaged and player.alive and self.nova_cooldown_timer <= 0.0:
            self._spawn_radial_nova(combat_system)
            # Enrage below 50% HP: faster nova cooldown
            self.nova_cooldown_timer = 3.0 if self.hp < self.max_hp * 0.5 else 4.4

        super().update(dt, player, tilemap, combat_system, rng)

    def _perform_attack(
        self,
        dir_x: float,
        dir_y: float,
        combat_system: CombatSystem,
    ) -> None:
        """Perform a wide boss cleave attack."""
        combat_system.melee_arcs.append(
            MeleeAttackArc(
                owner_is_player=False,
                origin_x=self.x,
                origin_y=self.y,
                dir_x=dir_x,
                dir_y=dir_y,
                radius=self.attack_range + 12.0,
                arc_angle_rad=math.radians(140),
                damage=self.damage,
                knockback_force=155.0,
                duration=0.20,
                color=(255, 70, 90),
                room_id=self.room_id,
            )
        )

    def _spawn_radial_nova(self, combat_system: CombatSystem) -> None:
        """Fire a ring of dark energy projectiles outward from the boss."""
        count = 10 if self.hp < self.max_hp * 0.5 else 8
        for i in range(count):
            ang = (math.pi * 2.0 * i) / count
            combat_system.projectiles.append(
                Projectile(
                    x=self.x,
                    y=self.y,
                    dir_x=math.cos(ang),
                    dir_y=math.sin(ang),
                    speed=self.projectile_speed,
                    damage=max(10, int(self.damage * 0.65)),
                    max_distance=185.0,
                    owner_is_player=False,
                    color=(245, 70, 110),
                    radius=4.5,
                    room_id=self.room_id,
                    room_bounds=self.room_bounds,
                )
            )

    def render(self, surface: pygame.Surface, camera_offset: tuple[int, int]) -> None:
        """Render the boss with an ominous dark-fantasy crown/aura."""
        if not self.alive:
            return
        cam_x, cam_y = camera_offset
        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))

        # Aura ring
        pygame.draw.circle(surface, (110, 20, 35), (sx, sy), self.half_size + 4, 1)
        super().render(surface, camera_offset)
        # Crown spikes
        pygame.draw.polygon(
            surface,
            (240, 195, 70),
            [
                (sx - 6, sy - self.half_size),
                (sx - 3, sy - self.half_size - 4),
                (sx, sy - self.half_size),
                (sx + 3, sy - self.half_size - 4),
                (sx + 6, sy - self.half_size),
            ],
        )
