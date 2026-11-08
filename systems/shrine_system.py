"""Shrine objective entities and stage ShrineSystem manager."""

from __future__ import annotations

from dataclasses import dataclass
import math
import pygame

from config.balance import (
    SHRINES_PER_SUBSTAGE,
    SHRINE_REWARD_CRYSTALS,
    SHRINE_REWARD_GOLD,
)
from config.settings import COLOR_SHRINE_ACTIVE, COLOR_SHRINE_INACTIVE, TILE_SIZE
from entities.enemy import Enemy
from world.tilemap import TileMap


@dataclass
class Shrine:
    """Independent Shrine objective entity located in a Shrine Room."""

    shrine_id: int
    room_id: int
    tile_x: int
    tile_y: int
    activated: bool = False
    interaction_radius: float = 28.0

    @property
    def world_pos(self) -> tuple[float, float]:
        """Return world pixel center of the shrine."""
        return (
            self.tile_x * TILE_SIZE + TILE_SIZE * 0.5,
            self.tile_y * TILE_SIZE + TILE_SIZE * 0.5,
        )

    @property
    def foot_y(self) -> float:
        """Return world Y coordinate of the shrine base for Y-sorting."""
        return self.world_pos[1] + 8.0

    def is_player_in_range(self, player_x: float, player_y: float) -> bool:
        """Return True if the player is close enough to interact with this shrine."""
        wx, wy = self.world_pos
        return math.hypot(player_x - wx, player_y - wy) <= self.interaction_radius

    def render(
        self,
        surface: pygame.Surface,
        camera_offset: tuple[int, int],
        guarded: bool,
    ) -> None:
        """Render the pixel-art ancient shrine obelisk and status aura."""
        cam_x, cam_y = camera_offset
        wx, wy = self.world_pos
        sx = int(round(wx - cam_x))
        sy = int(round(wy - cam_y))

        base_color = COLOR_SHRINE_ACTIVE if self.activated else COLOR_SHRINE_INACTIVE
        if guarded and not self.activated:
            base_color = (165, 65, 85)

        # Shrine pedestal
        pedestal_rect = pygame.Rect(sx - 8, sy - 4, 16, 12)
        pygame.draw.rect(surface, (52, 46, 66), pedestal_rect)
        pygame.draw.rect(surface, (95, 84, 118), pedestal_rect, 1)

        # Obelisk crystal core
        crystal_points = [
            (sx, sy - 12),
            (sx + 6, sy - 3),
            (sx, sy + 4),
            (sx - 6, sy - 3),
        ]
        pygame.draw.polygon(surface, base_color, crystal_points)
        pygame.draw.polygon(surface, (235, 240, 255), crystal_points, 1)


class ShrineSystem:
    """Manages the Shrine objectives in the active substage or stage."""

    def __init__(
        self,
        shrines: list[Shrine],
        required_count: int | None = None,
    ) -> None:
        self.shrines: list[Shrine] = shrines
        self.required_count: int = (
            required_count
            if required_count is not None
            else (len(shrines) if shrines else SHRINES_PER_SUBSTAGE)
        )

    @property
    def activated_count(self) -> int:
        """Return number of shrines activated so far in the current stage."""
        return sum(1 for s in self.shrines if s.activated)

    @property
    def all_activated(self) -> bool:
        """Return True when all required shrines in the stage are activated."""
        return self.activated_count >= self.required_count

    @staticmethod
    def is_shrine_guarded(shrine: Shrine, enemies: list[Enemy]) -> bool:
        """Return True if any living enemy remains in the shrine's room."""
        return any(e.alive and e.room_id == shrine.room_id for e in enemies)

    def get_interactable_shrine(
        self,
        player_x: float,
        player_y: float,
    ) -> Shrine | None:
        """Return an unactivated shrine within interaction range of the player, if any."""
        for shrine in self.shrines:
            if not shrine.activated and shrine.is_player_in_range(player_x, player_y):
                return shrine
        return None

    def try_activate_nearby_shrine(
        self,
        player_x: float,
        player_y: float,
        enemies: list[Enemy],
        tilemap: TileMap,
    ) -> tuple[bool, str, int, int]:
        """Attempt to activate a nearby shrine.

        Returns (activated, status_message, gold_reward, crystal_reward).
        """
        shrine = self.get_interactable_shrine(player_x, player_y)
        if shrine is None:
            return (False, "", 0, 0)

        if self.is_shrine_guarded(shrine, enemies):
            return (False, "Defeat the Shrine Guardians first!", 0, 0)

        shrine.activated = True
        if self.all_activated:
            tilemap.unlock_boss_gates()
            if self.required_count == 1:
                msg = (
                    f"Shrine Activated! "
                    f"+{SHRINE_REWARD_GOLD}G +{SHRINE_REWARD_CRYSTALS} Crystals"
                )
            else:
                msg = f"All {self.required_count} Shrines Activated! The Boss Gate is now UNLOCKED!"
        else:
            msg = (
                f"Shrine Activated ({self.activated_count}/{self.required_count})! "
                f"+{SHRINE_REWARD_GOLD}G +{SHRINE_REWARD_CRYSTALS} Crystals"
            )
        return (True, msg, SHRINE_REWARD_GOLD, SHRINE_REWARD_CRYSTALS)
