"""Central combat system resolving melee arcs, projectiles, and damage packets."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from combat.abilities import MeleeAttackArc
from combat.damage import DamagePacket, FloatingDamageNumber
from entities.projectile import Projectile

if TYPE_CHECKING:
    from entities.enemy import Enemy
    from entities.player import Player
    from world.tilemap import TileMap


class CombatSystem:
    """Manages active attacks, projectiles, hit detection, and combat visual feedback."""

    def __init__(self) -> None:
        self.melee_arcs: list[MeleeAttackArc] = []
        self.projectiles: list[Projectile] = []
        self.floating_numbers: list[FloatingDamageNumber] = []

    def clear(self) -> None:
        """Reset all active combat entities when changing stages."""
        self.melee_arcs.clear()
        self.projectiles.clear()
        self.floating_numbers.clear()

    def spawn_player_basic_attack(
        self,
        player: Player,
        dir_x: float,
        dir_y: float,
    ) -> None:
        """Trigger the player's basic melee or ranged attack toward (dir_x, dir_y)."""
        if player.stats.is_ranged_basic:
            self.projectiles.append(
                Projectile(
                    x=player.x + dir_x * 10.0,
                    y=player.y + dir_y * 10.0,
                    dir_x=dir_x,
                    dir_y=dir_y,
                    speed=195.0,
                    damage=player.stats.attack_damage,
                    max_distance=player.stats.attack_range,
                    owner_is_player=True,
                    color=player.stats.color,
                    room_id=player.current_room_id,
                )
            )
        else:
            self.melee_arcs.append(
                MeleeAttackArc(
                    owner_is_player=True,
                    origin_x=player.x,
                    origin_y=player.y,
                    dir_x=dir_x,
                    dir_y=dir_y,
                    radius=player.stats.attack_range,
                    arc_angle_rad=math.radians(115),
                    damage=player.stats.attack_damage,
                    knockback_force=140.0,
                    duration=0.14,
                    color=(245, 225, 145),
                    room_id=player.current_room_id,
                )
            )

    def spawn_player_skill(
        self,
        player: Player,
        skill_slot: int,
        dir_x: float,
        dir_y: float,
    ) -> None:
        """Execute active Skill 1 or Skill 2 for the player character."""
        skill_def = player.stats.skill_1 if skill_slot == 1 else player.stats.skill_2
        dmg = int(round(player.stats.attack_damage * skill_def.damage_multiplier))

        if player.stats.character_id == "warrior":
            if skill_slot == 1:
                self.melee_arcs.append(
                    MeleeAttackArc(
                        owner_is_player=True,
                        origin_x=player.x,
                        origin_y=player.y,
                        dir_x=dir_x,
                        dir_y=dir_y,
                        radius=skill_def.attack_range,
                        arc_angle_rad=math.radians(165),
                        damage=dmg,
                        knockback_force=210.0,
                        duration=0.20,
                        color=(255, 130, 80),
                        room_id=player.current_room_id,
                    )
                )
            else:
                self.melee_arcs.append(
                    MeleeAttackArc(
                        owner_is_player=True,
                        origin_x=player.x,
                        origin_y=player.y,
                        dir_x=dir_x,
                        dir_y=dir_y,
                        radius=skill_def.attack_range,
                        arc_angle_rad=math.pi * 2.0,
                        damage=dmg,
                        knockback_force=250.0,
                        duration=0.25,
                        color=(255, 200, 90),
                        room_id=player.current_room_id,
                    )
                )
        elif player.stats.character_id == "mage":
            if skill_slot == 1:
                for i in range(8):
                    ang = (math.pi * 2.0 * i) / 8.0
                    self.projectiles.append(
                        Projectile(
                            x=player.x,
                            y=player.y,
                            dir_x=math.cos(ang),
                            dir_y=math.sin(ang),
                            speed=170.0,
                            damage=dmg,
                            max_distance=skill_def.attack_range,
                            owner_is_player=True,
                            color=(110, 190, 255),
                            room_id=player.current_room_id,
                        )
                    )
            else:
                self.melee_arcs.append(
                    MeleeAttackArc(
                        owner_is_player=True,
                        origin_x=player.x,
                        origin_y=player.y,
                        dir_x=dir_x,
                        dir_y=dir_y,
                        radius=skill_def.attack_range,
                        arc_angle_rad=math.pi * 2.0,
                        damage=dmg,
                        knockback_force=220.0,
                        duration=0.28,
                        color=(175, 100, 255),
                        room_id=player.current_room_id,
                    )
                )
        else:  # Archer
            base_ang = math.atan2(dir_y, dir_x)
            if skill_slot == 1:
                for offset_deg in (-14, 0, 14):
                    ang = base_ang + math.radians(offset_deg)
                    self.projectiles.append(
                        Projectile(
                            x=player.x,
                            y=player.y,
                            dir_x=math.cos(ang),
                            dir_y=math.sin(ang),
                            speed=230.0,
                            damage=dmg,
                            max_distance=skill_def.attack_range,
                            owner_is_player=True,
                            color=(130, 240, 150),
                            room_id=player.current_room_id,
                        )
                    )
            else:
                for i in range(10):
                    ang = (math.pi * 2.0 * i) / 10.0
                    self.projectiles.append(
                        Projectile(
                            x=player.x,
                            y=player.y,
                            dir_x=math.cos(ang),
                            dir_y=math.sin(ang),
                            speed=210.0,
                            damage=dmg,
                            max_distance=skill_def.attack_range,
                            owner_is_player=True,
                            color=(160, 255, 180),
                            room_id=player.current_room_id,
                        )
                    )
                player.dash_cooldown_timer = 0.0

    def update(
        self,
        dt: float,
        player: Player,
        enemies: list[Enemy],
        tilemap: TileMap,
    ) -> list[Enemy]:
        """Update all active melee arcs, projectiles, and resolve combat hits.

        Returns a list of enemies killed during this frame.
        """
        killed_enemies: list[Enemy] = []

        # 1. Update melee arcs and check hits (enforcing Room Ownership isolation)
        remaining_arcs: list[MeleeAttackArc] = []
        for arc in self.melee_arcs:
            if arc.owner_is_player:
                arc.origin_x = player.x
                arc.origin_y = player.y
                for enemy in enemies:
                    if not enemy.alive or enemy.entity_id in arc.hit_entity_ids:
                        continue
                    if arc.room_id is not None and arc.room_id != enemy.room_id:
                        continue
                    if arc.contains_point(enemy.x, enemy.y, entity_radius=enemy.radius):
                        arc.hit_entity_ids.add(enemy.entity_id)
                        packet = DamagePacket(
                            amount=arc.damage,
                            source_x=player.x,
                            source_y=player.y,
                            knockback_force=arc.knockback_force,
                        )
                        died = enemy.take_damage(packet)
                        self.floating_numbers.append(
                            FloatingDamageNumber(
                                x=enemy.x,
                                y=enemy.y - enemy.radius,
                                text=str(arc.damage),
                                color=(255, 230, 120),
                            )
                        )
                        if died:
                            killed_enemies.append(enemy)
            else:
                same_room = (
                    arc.room_id is None
                    or player.current_room_id is None
                    or arc.room_id == player.current_room_id
                )
                if (
                    same_room
                    and player.alive
                    and 0 not in arc.hit_entity_ids
                    and arc.contains_point(player.x, player.y, entity_radius=player.radius)
                ):
                    arc.hit_entity_ids.add(0)
                    packet = DamagePacket(
                        amount=arc.damage,
                        source_x=arc.origin_x,
                        source_y=arc.origin_y,
                        knockback_force=arc.knockback_force,
                    )
                    if player.take_damage(packet):
                        self.floating_numbers.append(
                            FloatingDamageNumber(
                                x=player.x,
                                y=player.y - player.radius,
                                text=f"-{arc.damage}",
                                color=(255, 85, 85),
                            )
                        )

            if arc.update(dt):
                remaining_arcs.append(arc)
        self.melee_arcs = remaining_arcs

        # 2. Update projectiles and check collisions (enforcing Room Ownership isolation)
        remaining_projectiles: list[Projectile] = []
        for proj in self.projectiles:
            if not proj.update(dt, tilemap):
                continue

            hit_occurred = False
            if proj.owner_is_player:
                for enemy in enemies:
                    if not enemy.alive:
                        continue
                    if proj.room_id is not None and proj.room_id != enemy.room_id:
                        continue
                    if math.hypot(enemy.x - proj.x, enemy.y - proj.y) <= (
                        enemy.radius + proj.radius
                    ):
                        packet = DamagePacket(
                            amount=proj.damage,
                            source_x=proj.x,
                            source_y=proj.y,
                            knockback_force=95.0,
                        )
                        died = enemy.take_damage(packet)
                        self.floating_numbers.append(
                            FloatingDamageNumber(
                                x=enemy.x,
                                y=enemy.y - enemy.radius,
                                text=str(proj.damage),
                                color=(255, 230, 120),
                            )
                        )
                        if died:
                            killed_enemies.append(enemy)
                        hit_occurred = True
                        break
            else:
                same_room = (
                    proj.room_id is None
                    or player.current_room_id is None
                    or proj.room_id == player.current_room_id
                )
                if (
                    same_room
                    and player.alive
                    and math.hypot(player.x - proj.x, player.y - proj.y)
                    <= (player.radius + proj.radius)
                ):
                    packet = DamagePacket(
                        amount=proj.damage,
                        source_x=proj.x,
                        source_y=proj.y,
                        knockback_force=90.0,
                    )
                    if player.take_damage(packet):
                        self.floating_numbers.append(
                            FloatingDamageNumber(
                                x=player.x,
                                y=player.y - player.radius,
                                text=f"-{proj.damage}",
                                color=(255, 85, 85),
                            )
                        )
                    hit_occurred = True

            if not hit_occurred:
                remaining_projectiles.append(proj)
        self.projectiles = remaining_projectiles

        # 3. Update floating combat numbers
        self.floating_numbers = [
            fn for fn in self.floating_numbers if fn.update(dt)
        ]

        return killed_enemies

    def render(
        self,
        surface: pygame.Surface,
        camera_offset: tuple[int, int],
        font: pygame.font.Font,
    ) -> None:
        """Render melee slash arcs, projectiles, and floating damage text."""
        for arc in self.melee_arcs:
            arc.render(surface, camera_offset)
        for proj in self.projectiles:
            proj.render(surface, camera_offset)

        cam_x, cam_y = camera_offset
        for fn in self.floating_numbers:
            sx = int(fn.x - cam_x)
            sy = int(fn.y - cam_y)
            txt_surf = font.render(fn.text, False, fn.color)
            surface.blit(txt_surf, (sx - txt_surf.get_width() // 2, sy))
