"""Room data structures, room states, and room type definitions for dungeon generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RoomType(Enum):
    """Supported room types in THE FRACTURED GATE (preserving Phase 1 + Revision 2.0 types)."""

    # Phase 1 original types (preserved for full backward compatibility)
    ENTRANCE = "entrance"
    NORMAL_COMBAT = "normal_combat"
    ELITE_COMBAT = "elite_combat"
    SHRINE = "shrine"
    MINI_BOSS = "mini_boss"
    TREASURE = "treasure"
    BOSS = "boss"

    # Revision 2.0 Substage room categories
    ENEMY = "enemy"
    SPECIAL = "special"
    SHOP = "shop"
    CHEST = "chest"
    EXIT = "exit"
    TRANSITION = "transition"

    @property
    def is_enemy_room(self) -> bool:
        """Return True if this room type represents an enemy combat room."""
        return self in (
            RoomType.ENEMY,
            RoomType.NORMAL_COMBAT,
            RoomType.ELITE_COMBAT,
            RoomType.MINI_BOSS,
        )


class RoomState(Enum):
    """Reusable room state machine states for exploration and combat locking."""

    UNEXPLORED = "unexplored"
    EXPLORING = "exploring"
    COMBAT_LOCKED = "combat_locked"
    CLEARED = "cleared"
    COMPLETED = "completed"


@dataclass
class Room:
    """Represents a rectangular room within the dungeon grid (in tile coordinates)."""

    room_id: int
    x: int
    y: int
    width: int
    height: int
    room_type: RoomType = RoomType.NORMAL_COMBAT
    connected_room_ids: list[int] = field(default_factory=list)
    cleared: bool = False
    visited: bool = False
    is_mandatory: bool = False
    state: RoomState = RoomState.UNEXPLORED
    door_tiles: list[tuple[int, int]] = field(default_factory=list)
    trigger_margin: int = 2

    @property
    def right(self) -> int:
        """Return exclusive right tile coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Return exclusive bottom tile coordinate."""
        return self.y + self.height

    @property
    def center(self) -> tuple[int, int]:
        """Return the center tile coordinates (cx, cy) of the room."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def inner_bounds(self) -> tuple[int, int, int, int]:
        """Return inner floor bounds (x1, y1, x2, y2) inset by 1 tile from room edges."""
        return (self.x + 1, self.y + 1, self.right - 2, self.bottom - 2)

    @property
    def trigger_bounds(self) -> tuple[int, int, int, int]:
        """Return tile bounds (x1, y1, x2, y2) inset by trigger_margin for Phase 2.4 combat lock."""
        m = max(1, min(self.trigger_margin, min(self.width, self.height) // 2 - 1))
        return (self.x + m, self.y + m, self.right - 1 - m, self.bottom - 1 - m)

    def intersects(self, other: Room, padding: int = 0) -> bool:
        """Check whether this room overlaps another room, including a tile padding margin."""
        return not (
            self.right + padding <= other.x
            or other.right + padding <= self.x
            or self.bottom + padding <= other.y
            or other.bottom + padding <= self.y
        )

    def contains_tile(self, tx: int, ty: int) -> bool:
        """Return True if the tile (tx, ty) lies inside this room's floor area."""
        return self.x <= tx < self.right and self.y <= ty < self.bottom

    def contains_trigger_tile(self, tx: int, ty: int) -> bool:
        """Return True if the tile (tx, ty) lies inside the inner combat trigger boundary."""
        x1, y1, x2, y2 = self.trigger_bounds
        return x1 <= tx <= x2 and y1 <= ty <= y2
