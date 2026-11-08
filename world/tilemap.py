"""Tilemap representation, collision queries, walkability validation, and surface rendering."""

from __future__ import annotations

from collections import deque
from enum import IntEnum
import pygame

from config.settings import (
    COLOR_BG_VOID,
    COLOR_DOOR_LOCKED,
    COLOR_DOOR_UNLOCKED,
    COLOR_WALL_BORDER,
    TILE_SIZE,
)
from world.biome import BiomeConfig


class TileType(IntEnum):
    """Discrete tile types stored in the 2D dungeon grid."""

    VOID = 0
    FLOOR = 1
    WALL = 2
    CORRIDOR = 3
    BOSS_GATE_LOCKED = 4
    BOSS_GATE_UNLOCKED = 5


WALKABLE_TILES: frozenset[TileType] = frozenset(
    {
        TileType.FLOOR,
        TileType.CORRIDOR,
        TileType.BOSS_GATE_UNLOCKED,
    }
)


class TileMap:
    """Grid-based dungeon tilemap with collision checks and cached rendering."""

    def __init__(self, width: int, height: int, biome: BiomeConfig) -> None:
        self.width: int = width
        self.height: int = height
        self.biome: BiomeConfig = biome
        self.grid: list[list[TileType]] = [
            [TileType.VOID for _ in range(width)] for _ in range(height)
        ]
        self.boss_gate_tiles: list[tuple[int, int]] = []
        self._cached_surface: pygame.Surface | None = None
        self._surface_dirty: bool = True

    def in_bounds(self, tx: int, ty: int) -> bool:
        """Return True if (tx, ty) is inside the grid boundaries."""
        return 0 <= tx < self.width and 0 <= ty < self.height

    def get_tile(self, tx: int, ty: int) -> TileType:
        """Return the tile type at (tx, ty), or VOID if out of bounds."""
        if not self.in_bounds(tx, ty):
            return TileType.VOID
        return self.grid[ty][tx]

    def set_tile(self, tx: int, ty: int, tile_type: TileType) -> None:
        """Set the tile type at (tx, ty) if within bounds."""
        if self.in_bounds(tx, ty):
            self.grid[ty][tx] = tile_type
            self._surface_dirty = True

    def is_walkable(self, tx: int, ty: int, ignore_boss_lock: bool = False) -> bool:
        """Return True if an entity can walk on tile (tx, ty)."""
        tile = self.get_tile(tx, ty)
        if ignore_boss_lock and tile == TileType.BOSS_GATE_LOCKED:
            return True
        return tile in WALKABLE_TILES

    def is_solid(self, tx: int, ty: int) -> bool:
        """Return True if tile (tx, ty) blocks movement or projectiles."""
        return not self.is_walkable(tx, ty, ignore_boss_lock=False)

    def unlock_boss_gates(self) -> None:
        """Convert all locked boss gate tiles into unlocked walkable tiles."""
        changed = False
        for tx, ty in self.boss_gate_tiles:
            if self.get_tile(tx, ty) == TileType.BOSS_GATE_LOCKED:
                self.grid[ty][tx] = TileType.BOSS_GATE_UNLOCKED
                changed = True
        if changed:
            self._surface_dirty = True

    def get_solid_rects_in_region(
        self,
        rect: pygame.Rect,
        margin_tiles: int = 2,
    ) -> list[pygame.Rect]:
        """Return world-space rectangles for solid tiles overlapping or near rect."""
        min_tx = max(0, (rect.left // TILE_SIZE) - margin_tiles)
        max_tx = min(self.width - 1, (rect.right // TILE_SIZE) + margin_tiles)
        min_ty = max(0, (rect.top // TILE_SIZE) - margin_tiles)
        max_ty = min(self.height - 1, (rect.bottom // TILE_SIZE) + margin_tiles)

        solid_rects: list[pygame.Rect] = []
        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                if self.is_solid(tx, ty):
                    solid_rects.append(
                        pygame.Rect(
                            tx * TILE_SIZE,
                            ty * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                        )
                    )
        return solid_rects

    def reachable_tiles_from(
        self,
        start_tile: tuple[int, int],
        ignore_boss_lock: bool = True,
    ) -> set[tuple[int, int]]:
        """Perform 4-directional flood-fill (BFS) returning all walkable tiles from start_tile."""
        sx, sy = start_tile
        if not self.is_walkable(sx, sy, ignore_boss_lock=ignore_boss_lock):
            return set()

        visited: set[tuple[int, int]] = {(sx, sy)}
        queue: deque[tuple[int, int]] = deque([(sx, sy)])

        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and self.is_walkable(
                    nx, ny, ignore_boss_lock=ignore_boss_lock
                ):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        return visited

    def build_walls_around_floors(self) -> None:
        """Surround all FLOOR, CORRIDOR, and GATE tiles with WALL tiles where VOID exists."""
        floor_like = {
            TileType.FLOOR,
            TileType.CORRIDOR,
            TileType.BOSS_GATE_LOCKED,
            TileType.BOSS_GATE_UNLOCKED,
        }
        to_wall: list[tuple[int, int]] = []
        for ty in range(self.height):
            for tx in range(self.width):
                if self.grid[ty][tx] != TileType.VOID:
                    continue
                has_adjacent_floor = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nt = self.get_tile(tx + dx, ty + dy)
                        if nt in floor_like:
                            has_adjacent_floor = True
                            break
                    if has_adjacent_floor:
                        break
                if has_adjacent_floor:
                    to_wall.append((tx, ty))

        for tx, ty in to_wall:
            self.grid[ty][tx] = TileType.WALL
        self._surface_dirty = True

    def _rebuild_surface(self) -> None:
        """Render the full tilemap onto a single cached Surface for fast blitting."""
        pixel_w = self.width * TILE_SIZE
        pixel_h = self.height * TILE_SIZE
        surface = pygame.Surface((pixel_w, pixel_h))
        surface.fill(COLOR_BG_VOID)

        for ty in range(self.height):
            for tx in range(self.width):
                tile = self.grid[ty][tx]
                if tile == TileType.VOID:
                    continue

                px = tx * TILE_SIZE
                py = ty * TILE_SIZE
                rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)

                if tile == TileType.FLOOR:
                    is_checker = (tx + ty) % 2 == 0
                    color = (
                        self.biome.floor_color
                        if is_checker
                        else self.biome.floor_accent_color
                    )
                    pygame.draw.rect(surface, color, rect)
                    if (tx * 7 + ty * 13) % 11 == 0:
                        pygame.draw.rect(
                            surface,
                            self.biome.floor_accent_color,
                            pygame.Rect(px + 4, py + 4, 2, 2),
                        )
                elif tile == TileType.CORRIDOR:
                    pygame.draw.rect(surface, self.biome.corridor_color, rect)
                    if (tx + ty) % 3 == 0:
                        pygame.draw.rect(
                            surface,
                            self.biome.floor_color,
                            pygame.Rect(px + 6, py + 6, 3, 3),
                        )
                elif tile == TileType.WALL:
                    pygame.draw.rect(surface, self.biome.wall_top_color, rect)
                    front_rect = pygame.Rect(px, py + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2)
                    pygame.draw.rect(surface, self.biome.wall_front_color, front_rect)
                    pygame.draw.rect(surface, COLOR_WALL_BORDER, rect, 1)
                elif tile == TileType.BOSS_GATE_LOCKED:
                    pygame.draw.rect(surface, COLOR_DOOR_LOCKED, rect)
                    pygame.draw.rect(surface, (220, 90, 90), rect, 2)
                elif tile == TileType.BOSS_GATE_UNLOCKED:
                    pygame.draw.rect(surface, COLOR_DOOR_UNLOCKED, rect)
                    pygame.draw.rect(surface, (140, 230, 165), rect, 1)

        self._cached_surface = surface
        self._surface_dirty = False

    def render(self, target_surface: pygame.Surface, camera_offset: tuple[int, int]) -> None:
        """Blit the visible region of the cached tilemap surface onto target_surface."""
        if self._cached_surface is None or self._surface_dirty:
            self._rebuild_surface()
        assert self._cached_surface is not None

        cam_x, cam_y = camera_offset
        view_w, view_h = target_surface.get_size()
        source_rect = pygame.Rect(cam_x, cam_y, view_w, view_h)
        target_surface.blit(self._cached_surface, (0, 0), source_rect)
