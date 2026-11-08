"""2D Camera system following the player and lightweight dark-fantasy lighting vignette."""

from __future__ import annotations

import pygame

from config.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class Camera:
    """Smooth-following 2D camera operating in 640x360 internal pixel space."""

    def __init__(
        self,
        viewport_width: int = INTERNAL_WIDTH,
        viewport_height: int = INTERNAL_HEIGHT,
    ) -> None:
        self.viewport_width: int = viewport_width
        self.viewport_height: int = viewport_height
        self.x: float = 0.0
        self.y: float = 0.0

    @property
    def offset(self) -> tuple[int, int]:
        """Return integer (cam_x, cam_y) top-left offset for rendering."""
        return (int(round(self.x)), int(round(self.y)))

    def snap_to(self, target_x: float, target_y: float) -> None:
        """Immediately center the camera on (target_x, target_y)."""
        self.x = target_x - self.viewport_width * 0.5
        self.y = target_y - self.viewport_height * 0.5

    def update(self, target_x: float, target_y: float, dt: float) -> None:
        """Smoothly interpolate camera position toward target_x, target_y."""
        desired_x = target_x - self.viewport_width * 0.5
        desired_y = target_y - self.viewport_height * 0.5
        lerp_factor = min(1.0, 12.0 * dt)
        self.x += (desired_x - self.x) * lerp_factor
        self.y += (desired_y - self.y) * lerp_factor

    def window_to_world(
        self,
        window_pos: tuple[int, int],
        window_size: tuple[int, int],
    ) -> tuple[float, float]:
        """Convert actual window mouse coordinates to world coordinates."""
        win_w, win_h = max(1, window_size[0]), max(1, window_size[1])
        internal_x = (window_pos[0] / win_w) * self.viewport_width
        internal_y = (window_pos[1] / win_h) * self.viewport_height
        return (internal_x + self.x, internal_y + self.y)


class AtmosphericLighting:
    """Pre-baked radial vignette surface for low-CPU dark-fantasy torchlight ambiance."""

    def __init__(
        self,
        width: int = INTERNAL_WIDTH,
        height: int = INTERNAL_HEIGHT,
    ) -> None:
        self.surface: pygame.Surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._bake_vignette(width, height)

    def _bake_vignette(self, width: int, height: int) -> None:
        """Bake concentric alpha rings once at startup for zero per-frame allocation."""
        self.surface.fill((6, 4, 12, 115))
        cx, cy = width // 2, height // 2
        for radius, alpha in (
            (185, 85),
            (145, 55),
            (110, 28),
            (78, 0),
        ):
            pygame.draw.circle(self.surface, (0, 0, 0, alpha), (cx, cy), radius)

    def render(self, target_surface: pygame.Surface) -> None:
        """Blit the pre-baked vignette onto the internal canvas."""
        target_surface.blit(self.surface, (0, 0))
