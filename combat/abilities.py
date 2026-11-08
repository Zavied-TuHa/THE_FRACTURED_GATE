"""Active melee arcs, shockwaves, and ability executors for characters."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import pygame


@dataclass
class MeleeAttackArc:
    """Short-lived directional melee hitbox and visual slash indicator."""

    owner_is_player: bool
    origin_x: float
    origin_y: float
    dir_x: float
    dir_y: float
    radius: float
    arc_angle_rad: float
    damage: int
    knockback_force: float = 135.0
    duration: float = 0.14
    elapsed: float = 0.0
    color: tuple[int, int, int] = (240, 220, 150)
    hit_entity_ids: set[int] = field(default_factory=set)
    room_id: int | None = None

    def update(self, dt: float) -> bool:
        """Advance attack timer; return True while active."""
        self.elapsed += dt
        return self.elapsed < self.duration

    def contains_point(self, px: float, py: float, entity_radius: float = 6.0) -> bool:
        """Check if a target point with entity_radius falls within the directional arc."""
        dx = px - self.origin_x
        dy = py - self.origin_y
        dist = math.hypot(dx, dy)
        if dist > self.radius + entity_radius:
            return False
        if self.arc_angle_rad >= math.pi * 1.95 or dist < 4.0:
            return True

        nx = dx / dist
        ny = dy / dist
        dot = max(-1.0, min(1.0, nx * self.dir_x + ny * self.dir_y))
        angle = math.acos(dot)
        return angle <= (self.arc_angle_rad * 0.5)

    def render(self, surface: pygame.Surface, camera_offset: tuple[int, int]) -> None:
        """Render the pixel-art slash arc or radial shockwave."""
        cam_x, cam_y = camera_offset
        sx = int(self.origin_x - cam_x)
        sy = int(self.origin_y - cam_y)

        if self.arc_angle_rad >= math.pi * 1.95:
            progress = min(1.0, self.elapsed / max(0.01, self.duration))
            current_r = max(4, int(self.radius * (0.4 + 0.6 * progress)))
            pygame.draw.circle(surface, self.color, (sx, sy), current_r, 2)
            return

        base_angle = math.atan2(self.dir_y, self.dir_x)
        half_arc = self.arc_angle_rad * 0.5
        steps = 7
        points: list[tuple[int, int]] = [(sx, sy)]
        for i in range(steps + 1):
            t = -half_arc + (self.arc_angle_rad * i / steps)
            ang = base_angle + t
            px = int(sx + math.cos(ang) * self.radius)
            py = int(sy + math.sin(ang) * self.radius)
            points.append((px, py))

        if len(points) >= 3:
            pygame.draw.polygon(surface, self.color, points, 1)
            pygame.draw.lines(surface, self.color, False, points[1:], 2)
