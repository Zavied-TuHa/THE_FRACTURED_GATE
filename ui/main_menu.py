"""Dark medieval fantasy Main Menu screen."""

from __future__ import annotations

import pygame

from config.settings import (
    COLOR_UI_BG,
    COLOR_UI_BORDER,
    COLOR_UI_CRYSTAL,
    COLOR_UI_GOLD,
    COLOR_UI_MUTED,
    COLOR_UI_PANEL,
    COLOR_UI_TEXT,
    GAME_TITLE,
    GAME_VERSION,
    INTERNAL_HEIGHT,
    INTERNAL_WIDTH,
)
from systems.progression import ProgressionManager


class MainMenuScreen:
    """Renders and processes input for the Main Menu."""

    def __init__(self) -> None:
        self.options: list[str] = [
            "Enter the Gate (Start Run)",
            "Quit to Desktop",
        ]
        self.selected_index: int = 0

    def handle_keydown(self, key: int) -> str | None:
        """Process keyboard navigation; return selected action ID or None."""
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_index = (self.selected_index - 1) % len(self.options)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = (self.selected_index + 1) % len(self.options)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.selected_index == 0:
                return "character_selection"
            return "quit"
        return None

    def render(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        progression: ProgressionManager,
    ) -> None:
        """Render the gothic dark-fantasy Main Menu onto the internal 640x360 canvas."""
        surface.fill(COLOR_UI_BG)

        # Outer gothic border frame
        frame_rect = pygame.Rect(16, 16, INTERNAL_WIDTH - 32, INTERNAL_HEIGHT - 32)
        pygame.draw.rect(surface, COLOR_UI_PANEL, frame_rect)
        pygame.draw.rect(surface, COLOR_UI_BORDER, frame_rect, 2)

        # Decorative archway header
        arch_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 190, 42, 380, 74)
        pygame.draw.rect(surface, (22, 18, 30), arch_rect)
        pygame.draw.rect(surface, COLOR_UI_BORDER, arch_rect, 1)

        title_surf = title_font.render(GAME_TITLE, False, COLOR_UI_GOLD)
        surface.blit(
            title_surf,
            (INTERNAL_WIDTH // 2 - title_surf.get_width() // 2, 54),
        )

        subtitle_surf = small_font.render(
            "Dark Fantasy Procedural Action Roguelike",
            False,
            COLOR_UI_MUTED,
        )
        surface.blit(
            subtitle_surf,
            (INTERNAL_WIDTH // 2 - subtitle_surf.get_width() // 2, 88),
        )

        # Menu options
        for idx, label in enumerate(self.options):
            is_selected = idx == self.selected_index
            btn_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 135, 152 + idx * 42, 270, 32)
            bg_col = (48, 38, 66) if is_selected else (26, 22, 36)
            border_col = COLOR_UI_GOLD if is_selected else COLOR_UI_BORDER
            pygame.draw.rect(surface, bg_col, btn_rect)
            pygame.draw.rect(surface, border_col, btn_rect, 1)

            prefix = "> " if is_selected else "  "
            txt = body_font.render(f"{prefix}{label}", False, COLOR_UI_TEXT)
            surface.blit(
                txt,
                (
                    btn_rect.centerx - txt.get_width() // 2,
                    btn_rect.centery - txt.get_height() // 2,
                ),
            )

        # Persistent progression summary bar
        stats_text = (
            f"Gold: {progression.data.gold}   |   "
            f"Blue Crystals: {progression.data.blue_crystals}   |   "
            f"Runs: {progression.data.runs_started}   |   "
            f"Victories: {progression.data.runs_completed}"
        )
        stats_surf = small_font.render(stats_text, False, COLOR_UI_CRYSTAL)
        surface.blit(
            stats_surf,
            (INTERNAL_WIDTH // 2 - stats_surf.get_width() // 2, INTERNAL_HEIGHT - 64),
        )

        hint_surf = small_font.render(
            f"[W/S or Up/Down] Navigate   [Enter/Space] Confirm   ({GAME_VERSION})",
            False,
            COLOR_UI_MUTED,
        )
        surface.blit(
            hint_surf,
            (INTERNAL_WIDTH // 2 - hint_surf.get_width() // 2, INTERNAL_HEIGHT - 40),
        )
