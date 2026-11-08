"""Pause Menu, Treasure Room, Victory Screen, and Game Over Screen."""

from __future__ import annotations

import pygame

from config.settings import (
    COLOR_TREASURE_CHEST,
    COLOR_UI_BG,
    COLOR_UI_BORDER,
    COLOR_UI_CRYSTAL,
    COLOR_UI_GOLD,
    COLOR_UI_MUTED,
    COLOR_UI_PANEL,
    COLOR_UI_TEXT,
    INTERNAL_HEIGHT,
    INTERNAL_WIDTH,
)
from systems.run_manager import RunManager


class PauseMenuOverlay:
    """Modal Pause Menu overlay rendered over gameplay."""

    def __init__(self) -> None:
        self.options: list[str] = [
            "Resume Run",
            "Quit Run to Character Selection",
            "Quit Run to Main Menu",
        ]
        self.selected_index: int = 0

    def reset(self) -> None:
        """Reset pause menu selection to 'Resume Run' when opened."""
        self.selected_index = 0

    def handle_keydown(self, key: int) -> str | None:
        """Process pause menu navigation, separating Resume from Quit flows."""
        if key == pygame.K_ESCAPE:
            return "resume"
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_index = (self.selected_index - 1) % len(self.options)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = (self.selected_index + 1) % len(self.options)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.selected_index == 0:
                return "resume"
            if self.selected_index == 1:
                return "pause_quit_character_selection"
            return "pause_quit_main_menu"
        return None

    def render(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
    ) -> None:
        """Render semi-transparent backdrop and pause menu panel."""
        overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 6, 12, 185))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(INTERNAL_WIDTH // 2 - 140, 86, 280, 188)
        pygame.draw.rect(surface, COLOR_UI_PANEL, panel)
        pygame.draw.rect(surface, COLOR_UI_BORDER, panel, 2)

        t_surf = title_font.render("PAUSED", False, COLOR_UI_GOLD)
        surface.blit(t_surf, (panel.centerx - t_surf.get_width() // 2, panel.y + 18))

        for idx, opt in enumerate(self.options):
            sel = idx == self.selected_index
            col = COLOR_UI_GOLD if sel else COLOR_UI_TEXT
            prefix = "> " if sel else "  "
            o_surf = body_font.render(f"{prefix}{opt}", False, col)
            surface.blit(
                o_surf,
                (panel.centerx - o_surf.get_width() // 2, panel.y + 68 + idx * 32),
            )


class TreasureRoomScreen:
    """Interactive post-Stage-3 Treasure Room where the player claims the Grand Chest."""

    def handle_keydown(self, key: int, run_manager: RunManager) -> str | None:
        """Press F or Enter to open chest, then Enter/Space to continue."""
        if key == pygame.K_f and not run_manager.treasure_collected:
            run_manager.claim_treasure_chest()
            return None
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if not run_manager.treasure_collected:
                run_manager.claim_treasure_chest()
                return None
            return "victory"
        return None

    def render(
        self,
        surface: pygame.Surface,
        run_manager: RunManager,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> None:
        """Render the Sanctum Treasure Room and Grand Chest."""
        surface.fill(COLOR_UI_BG)
        panel = pygame.Rect(40, 28, INTERNAL_WIDTH - 80, INTERNAL_HEIGHT - 56)
        pygame.draw.rect(surface, COLOR_UI_PANEL, panel)
        pygame.draw.rect(surface, COLOR_UI_GOLD, panel, 2)

        title = title_font.render("SANCTUM TREASURE CHAMBER", False, COLOR_UI_GOLD)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2, 48))

        # Draw Grand Treasure Chest sprite
        chest_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 28, 118, 56, 42)
        chest_col = (140, 225, 130) if run_manager.treasure_collected else COLOR_TREASURE_CHEST
        pygame.draw.rect(surface, chest_col, chest_rect)
        pygame.draw.rect(surface, (255, 240, 180), chest_rect, 2)
        pygame.draw.rect(
            surface,
            (40, 30, 20),
            pygame.Rect(chest_rect.centerx - 5, chest_rect.centery - 4, 10, 10),
        )

        if not run_manager.treasure_collected:
            msg = body_font.render(
                "Press [F] or [Enter] to Open the Grand Runic Chest!",
                False,
                COLOR_UI_TEXT,
            )
            surface.blit(msg, (INTERNAL_WIDTH // 2 - msg.get_width() // 2, 188))
        else:
            reward_msg = body_font.render(
                "Chest Opened! +150 Gold & +50 Blue Crystals Claimed!",
                False,
                COLOR_UI_CRYSTAL,
            )
            surface.blit(
                reward_msg,
                (INTERNAL_WIDTH // 2 - reward_msg.get_width() // 2, 184),
            )
            cont_msg = small_font.render(
                "Press [Enter] or [Space] to Proceed to Victory Summary",
                False,
                COLOR_UI_GOLD,
            )
            surface.blit(
                cont_msg,
                (INTERNAL_WIDTH // 2 - cont_msg.get_width() // 2, 222),
            )


class EndRunScreen:
    """Renders either the Victory Screen or the Game Over Screen."""

    def __init__(self, is_victory: bool) -> None:
        self.is_victory: bool = is_victory

    def handle_keydown(self, key: int) -> str | None:
        """Return to Character Selection or Main Menu."""
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            return "character_selection"
        if key == pygame.K_ESCAPE:
            return "main_menu"
        return None

    def render(
        self,
        surface: pygame.Surface,
        run_manager: RunManager,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> None:
        """Render run summary statistics and navigation prompts."""
        surface.fill(COLOR_UI_BG)
        panel = pygame.Rect(56, 36, INTERNAL_WIDTH - 112, INTERNAL_HEIGHT - 72)
        pygame.draw.rect(surface, COLOR_UI_PANEL, panel)
        border_col = COLOR_UI_GOLD if self.is_victory else (200, 50, 60)
        pygame.draw.rect(surface, border_col, panel, 2)

        heading_text = (
            "VICTORY - THE GATE IS SEALED"
            if self.is_victory
            else "YOU HAVE FALLEN IN THE DARK"
        )
        h_surf = title_font.render(heading_text, False, border_col)
        surface.blit(h_surf, (INTERNAL_WIDTH // 2 - h_surf.get_width() // 2, 62))

        summary_lines = [
            f"Run Seed: {run_manager.run_seed}",
            f"Stage Reached: Stage {run_manager.current_stage_index} - Substage {run_manager.current_substage_index}",
            f"Shrines Activated: {run_manager.total_shrines_activated} / 15",
            f"Enemies Vanquished: {run_manager.enemies_slain}",
            f"Gold Earned This Run: +{run_manager.run_gold_earned} G",
            f"Blue Crystals Earned This Run: +{run_manager.run_crystals_earned} C",
        ]
        for idx, line in enumerate(summary_lines):
            l_surf = body_font.render(line, False, COLOR_UI_TEXT)
            surface.blit(
                l_surf,
                (INTERNAL_WIDTH // 2 - l_surf.get_width() // 2, 104 + idx * 22),
            )

        prompt = small_font.render(
            "[Enter/Space] Return to Character Selection     [Esc] Main Menu",
            False,
            COLOR_UI_MUTED,
        )
        surface.blit(
            prompt,
            (INTERNAL_WIDTH // 2 - prompt.get_width() // 2, INTERNAL_HEIGHT - 64),
        )
