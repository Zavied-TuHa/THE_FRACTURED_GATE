"""Character Selection and Permanent Progression unlock screen."""

from __future__ import annotations

import pygame

from characters.archer import get_all_character_stats
from config.settings import (
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
from systems.economy import EconomyManager
from systems.progression import ProgressionManager


class CharacterSelectionScreen:
    """Allows selecting a character, unlocking classes/skills, and starting a run."""

    CHARACTER_ORDER: tuple[str, ...] = ("warrior", "mage", "archer")

    def __init__(self) -> None:
        self.selected_index: int = 0
        self.feedback_message: str = ""

    @property
    def selected_character_id(self) -> str:
        """Return currently highlighted character ID."""
        return self.CHARACTER_ORDER[self.selected_index]

    def handle_keydown(
        self,
        key: int,
        progression: ProgressionManager,
    ) -> str | None:
        """Handle navigation, character/skill unlocks, and run launch."""
        if key in (pygame.K_LEFT, pygame.K_a):
            self.selected_index = (self.selected_index - 1) % len(self.CHARACTER_ORDER)
            self.feedback_message = ""
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.selected_index = (self.selected_index + 1) % len(self.CHARACTER_ORDER)
            self.feedback_message = ""
        elif key == pygame.K_ESCAPE:
            return "main_menu"
        elif key == pygame.K_u:
            char_id = self.selected_character_id
            if progression.is_character_unlocked(char_id):
                self.feedback_message = f"{char_id.title()} is already unlocked."
            elif progression.unlock_character(char_id):
                self.feedback_message = f"Unlocked {char_id.title()}!"
            else:
                cost = EconomyManager.get_character_unlock_cost(char_id)
                self.feedback_message = f"Need {cost} Blue Crystals to unlock {char_id.title()}."
        elif key == pygame.K_1:
            char_id = self.selected_character_id
            if progression.unlock_skill(char_id, "skill_1"):
                self.feedback_message = "Unlocked Skill 1 [Q]!"
            else:
                cost = EconomyManager.get_skill_unlock_cost(char_id, "skill_1")
                self.feedback_message = f"Cannot unlock Skill 1 (Requires unlocked hero & {cost} Gold)."
        elif key == pygame.K_2:
            char_id = self.selected_character_id
            if progression.unlock_skill(char_id, "skill_2"):
                self.feedback_message = "Unlocked Skill 2 [E]!"
            else:
                cost = EconomyManager.get_skill_unlock_cost(char_id, "skill_2")
                self.feedback_message = f"Cannot unlock Skill 2 (Requires unlocked hero & {cost} Gold)."
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            char_id = self.selected_character_id
            if progression.is_character_unlocked(char_id):
                return f"start_run:{char_id}"
            self.feedback_message = "Character is locked! Press [U] to unlock with Blue Crystals."
        return None

    def render(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        progression: ProgressionManager,
    ) -> None:
        """Render the three character cards, stats, skill unlock statuses, and controls."""
        surface.fill(COLOR_UI_BG)
        all_stats = get_all_character_stats()

        header = title_font.render("CHOOSE YOUR CHAMPION", False, COLOR_UI_GOLD)
        surface.blit(header, (INTERNAL_WIDTH // 2 - header.get_width() // 2, 16))

        curr_str = (
            f"Gold: {progression.data.gold} G     "
            f"Blue Crystals: {progression.data.blue_crystals} C"
        )
        curr_surf = body_font.render(curr_str, False, COLOR_UI_CRYSTAL)
        surface.blit(curr_surf, (INTERNAL_WIDTH // 2 - curr_surf.get_width() // 2, 44))

        card_w = 188
        card_h = 224
        spacing = 14
        total_w = len(self.CHARACTER_ORDER) * card_w + (len(self.CHARACTER_ORDER) - 1) * spacing
        start_x = (INTERNAL_WIDTH - total_w) // 2
        card_y = 72

        for idx, char_id in enumerate(self.CHARACTER_ORDER):
            stats = all_stats[char_id]
            unlocked = progression.is_character_unlocked(char_id)
            selected = idx == self.selected_index

            cx = start_x + idx * (card_w + spacing)
            rect = pygame.Rect(cx, card_y, card_w, card_h)
            bg_col = (38, 32, 52) if selected else COLOR_UI_PANEL
            border_col = COLOR_UI_GOLD if selected else COLOR_UI_BORDER
            pygame.draw.rect(surface, bg_col, rect)
            pygame.draw.rect(surface, border_col, rect, 2 if selected else 1)

            # Character sprite preview box (32x32 Chibi sprite for Warrior)
            if char_id == "warrior":
                from systems.asset_manager import AssetManager

                ctrl = AssetManager.get_instance().create_character_animation_controller("warrior")
                frame = ctrl.get_current_frame()
                surface.blit(frame, (cx + card_w // 2 - 16, card_y + 8))
            else:
                avatar_rect = pygame.Rect(cx + card_w // 2 - 12, card_y + 12, 24, 24)
                pygame.draw.rect(surface, stats.color if unlocked else (75, 70, 85), avatar_rect)
                pygame.draw.rect(surface, COLOR_UI_TEXT, avatar_rect, 1)

            name_surf = body_font.render(stats.name, False, COLOR_UI_TEXT)
            surface.blit(name_surf, (cx + card_w // 2 - name_surf.get_width() // 2, card_y + 42))

            role_surf = small_font.render(stats.role, False, COLOR_UI_MUTED)
            surface.blit(role_surf, (cx + card_w // 2 - role_surf.get_width() // 2, card_y + 60))

            status_col = (110, 225, 130) if unlocked else (235, 95, 95)
            cost_crystals = EconomyManager.get_character_unlock_cost(char_id)
            status_str = "UNLOCKED" if unlocked else f"LOCKED ({cost_crystals} Crystals [U])"
            st_surf = small_font.render(status_str, False, status_col)
            surface.blit(st_surf, (cx + card_w // 2 - st_surf.get_width() // 2, card_y + 78))

            # Stats lines
            lines = [
                f"HP: {stats.max_hp}   SPD: {int(stats.move_speed)}",
                f"ATK: {stats.attack_damage}   CD: {stats.attack_cooldown:.2f}s",
            ]
            for l_i, line in enumerate(lines):
                ls = small_font.render(line, False, COLOR_UI_TEXT)
                surface.blit(ls, (cx + 12, card_y + 102 + l_i * 16))

            # Skills status
            s1_ok = progression.is_skill_unlocked(char_id, "skill_1")
            s2_ok = progression.is_skill_unlocked(char_id, "skill_2")
            s1_cost = EconomyManager.get_skill_unlock_cost(char_id, "skill_1")
            s2_cost = EconomyManager.get_skill_unlock_cost(char_id, "skill_2")

            s1_txt = f"[Q] {stats.skill_1.name}: " + ("Ready" if s1_ok else f"{s1_cost}G [1]")
            s2_txt = f"[E] {stats.skill_2.name}: " + ("Ready" if s2_ok else f"{s2_cost}G [2]")

            s1_surf = small_font.render(
                s1_txt, False, COLOR_UI_GOLD if s1_ok else COLOR_UI_MUTED
            )
            s2_surf = small_font.render(
                s2_txt, False, COLOR_UI_GOLD if s2_ok else COLOR_UI_MUTED
            )
            surface.blit(s1_surf, (cx + 10, card_y + 146))
            surface.blit(s2_surf, (cx + 10, card_y + 166))

            basic_surf = small_font.render("Basic Attack [LMB]: Unlocked", False, (150, 215, 165))
            surface.blit(basic_surf, (cx + 10, card_y + 192))

        if self.feedback_message:
            fb_surf = small_font.render(self.feedback_message, False, COLOR_UI_GOLD)
            surface.blit(
                fb_surf,
                (INTERNAL_WIDTH // 2 - fb_surf.get_width() // 2, INTERNAL_HEIGHT - 50),
            )

        footer = small_font.render(
            "[A/D] Select  [Enter] Start Run  [U] Unlock Hero  [1/2] Unlock Skill 1/2  [Esc] Back",
            False,
            COLOR_UI_MUTED,
        )
        surface.blit(
            footer,
            (INTERNAL_WIDTH // 2 - footer.get_width() // 2, INTERNAL_HEIGHT - 26),
        )
