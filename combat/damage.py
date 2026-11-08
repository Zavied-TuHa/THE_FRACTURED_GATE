"""Damage calculation, knockback vectors, and floating combat text."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class DamagePacket:
    """Encapsulates damage, knockback force, and directional vector for an attack."""

    amount: int
    source_x: float
    source_y: float
    knockback_force: float = 110.0
    is_critical: bool = False

    def compute_knockback_vector(
        self,
        target_x: float,
        target_y: float,
        knockback_resistance: float = 0.0,
    ) -> tuple[float, float]:
        """Compute (vx, vy) knockback velocity away from the damage source."""
        dx = target_x - self.source_x
        dy = target_y - self.source_y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            dx, dy = 1.0, 0.0
        else:
            dx /= dist
            dy /= dist

        effective_force = self.knockback_force * max(0.0, 1.0 - knockback_resistance)
        return (dx * effective_force, dy * effective_force)


@dataclass
class FloatingDamageNumber:
    """Visual floating damage text that rises and fades out."""

    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    lifetime: float = 0.55
    elapsed: float = 0.0

    def update(self, dt: float) -> bool:
        """Advance timer and vertical position; return True while still alive."""
        self.elapsed += dt
        self.y -= 22.0 * dt
        return self.elapsed < self.lifetime
