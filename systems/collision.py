"""Axis-separated tilemap collision resolution for entities."""

from __future__ import annotations

import pygame

from world.tilemap import TileMap


def move_with_tile_collision(
    x: float,
    y: float,
    vx: float,
    vy: float,
    dt: float,
    half_size: int,
    tilemap: TileMap,
) -> tuple[float, float]:
    """Move a square hitbox centered at (x, y) by (vx * dt, vy * dt) resolving wall collisions."""
    # Resolve X axis
    new_x = x + vx * dt
    rect_x = pygame.Rect(
        int(round(new_x)) - half_size,
        int(round(y)) - half_size,
        half_size * 2,
        half_size * 2,
    )
    for wall in tilemap.get_solid_rects_in_region(rect_x):
        if rect_x.colliderect(wall):
            if vx > 0:
                rect_x.right = wall.left
            elif vx < 0:
                rect_x.left = wall.right
            new_x = float(rect_x.centerx)

    # Resolve Y axis
    new_y = y + vy * dt
    rect_y = pygame.Rect(
        int(round(new_x)) - half_size,
        int(round(new_y)) - half_size,
        half_size * 2,
        half_size * 2,
    )
    for wall in tilemap.get_solid_rects_in_region(rect_y):
        if rect_y.colliderect(wall):
            if vy > 0:
                rect_y.bottom = wall.top
            elif vy < 0:
                rect_y.top = wall.bottom
            new_y = float(rect_y.centery)

    return (new_x, new_y)
