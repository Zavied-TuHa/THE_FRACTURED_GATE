"""Projectile entity for ranged player and enemy attacks with room ownership isolation."""

from __future__ import annotations

from dataclasses import dataclass
import math
import pygame

from config.settings import TILE_SIZE
from world.tilemap import TileMap


@dataclass
class Projectile:
    """Linear projectile with range limit, wall collision, and room ownership isolation."""

    x: float
    y: float
    dir_x: float
    dir_y: float
    speed: float
    damage: int
    max_distance: float
    owner_is_player: bool
    color: tuple[int, int, int] = (230, 190, 90)
    radius: float = 3.5
    traveled: float = 0.0
    room_id: int | None = None
    room_bounds: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        mag = math.hypot(self.dir_x, self.dir_y)
        if mag > 1e-5:
            self.dir_x /= mag
            self.dir_y /= mag
        else:
            self.dir_x, self.dir_y = 1.0, 0.0

    def update(self, dt: float, tilemap: TileMap) -> bool:
        """Advance position; return False if hitting a wall, leaving room_bounds, or exceeding range."""
        step = self.speed * dt
        self.x += self.dir_x * step
        self.y += self.dir_y * step
        self.traveled += step

        if self.traveled >= self.max_distance:
            return False

        if self.room_bounds is not None:
            min_x, min_y, max_x, max_y = self.room_bounds
            if not (min_x <= self.x <= max_x and min_y <= self.y <= max_y):
                return False

        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        if tilemap.is_solid(tx, ty):
            return False
        return True

    def render(self, surface: pygame.Surface, camera_offset: tuple[int, int]) -> None:
        """Render pixel projectile with bright core."""
        cam_x, cam_y = camera_offset
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        pygame.draw.circle(surface, self.color, (sx, sy), int(self.radius))
        pygame.draw.circle(surface, (255, 250, 235), (sx, sy), max(1, int(self.radius) - 2))
