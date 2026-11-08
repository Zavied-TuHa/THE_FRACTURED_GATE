"""Corridor representation connecting two dungeon rooms."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Corridor:
    """An orthogonal corridor connecting start_tile to end_tile with configurable width."""

    corridor_id: int
    room_a_id: int
    room_b_id: int
    start_tile: tuple[int, int]
    end_tile: tuple[int, int]
    width: int = 2
    horizontal_first: bool = True
    tiles: set[tuple[int, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.tiles:
            self.tiles = self._compute_tiles()

    @property
    def bend_tile(self) -> tuple[int, int]:
        """Return the elbow bend coordinate of the L-shaped corridor."""
        x1, y1 = self.start_tile
        x2, y2 = self.end_tile
        if self.horizontal_first:
            return (x2, y1)
        return (x1, y2)

    def _compute_tiles(self) -> set[tuple[int, int]]:
        """Carve orthogonal horizontal and vertical segments with configured width."""
        carved: set[tuple[int, int]] = set()
        x1, y1 = self.start_tile
        x2, y2 = self.end_tile
        bx, by = self.bend_tile

        self._carve_segment(carved, x1, y1, bx, by)
        self._carve_segment(carved, bx, by, x2, y2)
        return carved

    def _carve_segment(
        self,
        carved: set[tuple[int, int]],
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> None:
        """Add tiles along an axis-aligned segment expanded by corridor width."""
        half_low = -(self.width // 2)
        half_high = self.width + half_low

        if y1 == y2:
            min_x, max_x = min(x1, x2), max(x1, x2)
            for x in range(min_x, max_x + 1):
                for dy in range(half_low, half_high):
                    for dx in range(half_low, half_high):
                        carved.add((x + dx, y1 + dy))
        elif x1 == x2:
            min_y, max_y = min(y1, y2), max(y1, y2)
            for y in range(min_y, max_y + 1):
                for dx in range(half_low, half_high):
                    for dy in range(half_low, half_high):
                        carved.add((x1 + dx, y + dy))
