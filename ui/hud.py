"""Gameplay HUD displaying health, currencies, stage, shrines, skill cooldowns, and boss bar."""

from __future__ import annotations

import pygame

from config.balance import (
    REQUIRED_SHRINES_PER_STAGE_V2,
    SUBSTAGES_PER_STAGE,
    TOTAL_STAGES_PER_RUN,
)
from config.settings import (
    COLOR_UI_BORDER,
    COLOR_UI_BOSS_HP,
    COLOR_UI_CRYSTAL,
    COLOR_UI_GOLD,
    COLOR_UI_HP_BG,
    COLOR_UI_HP_FILL,
    COLOR_UI_MUTED,
    COLOR_UI_PANEL,
    COLOR_UI_TEXT,
    INTERNAL_HEIGHT,
    INTERNAL_WIDTH,
)
from systems.run_manager import RunManager
from world.room import RoomType


class GameplayHUD:
    """Renders the dark medieval fantasy heads-up display during dungeon exploration."""

    def render(
        self,
        surface: pygame.Surface,
        run_manager: RunManager,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> None:
        """Draw health bar, currency counters, stage/shrine tracker, skill slots, and boss bar."""
        player = run_manager.player
        dungeon = run_manager.dungeon
        shrine_sys = run_manager.shrine_system
        if player is None or dungeon is None or shrine_sys is None:
            return

        # 1. Top-Left Panel: Player Health & Currencies
        tl_rect = pygame.Rect(8, 8, 178, 54)
        pygame.draw.rect(surface, COLOR_UI_PANEL, tl_rect)
        pygame.draw.rect(surface, COLOR_UI_BORDER, tl_rect, 1)

        hp_bar_bg = pygame.Rect(14, 14, 164, 14)
        pygame.draw.rect(surface, COLOR_UI_HP_BG, hp_bar_bg)
        hp_ratio = max(0.0, min(1.0, player.hp / max(1, player.max_hp)))
        hp_bar_fill = pygame.Rect(14, 14, int(164 * hp_ratio), 14)
        pygame.draw.rect(surface, COLOR_UI_HP_FILL, hp_bar_fill)
        pygame.draw.rect(surface, COLOR_UI_BORDER, hp_bar_bg, 1)

        hp_txt = small_font.render(f"HP {player.hp}/{player.max_hp}", False, COLOR_UI_TEXT)
        surface.blit(hp_txt, (18, 15))

        gold_txt = small_font.render(
            f"Gold: {run_manager.progression.data.gold}",
            False,
            COLOR_UI_GOLD,
        )
        crys_txt = small_font.render(
            f"Crystals: {run_manager.progression.data.blue_crystals}",
            False,
            COLOR_UI_CRYSTAL,
        )
        surface.blit(gold_txt, (14, 36))
        surface.blit(crys_txt, (96, 36))

        # 2. Top-Right Panel: Stage, Substage & Shrine Objective Progress + Mini-map
        tr_rect = pygame.Rect(INTERNAL_WIDTH - 224, 8, 216, 48)
        pygame.draw.rect(surface, COLOR_UI_PANEL, tr_rect)
        pygame.draw.rect(surface, COLOR_UI_BORDER, tr_rect, 1)

        if run_manager.in_boss_room:
            stage_str = (
                f"Stage {run_manager.current_stage_index}/{TOTAL_STAGES_PER_RUN} BOSS: "
                f"{dungeon.biome.name}"
            )
        else:
            stage_str = (
                f"S{run_manager.current_stage_index}/{TOTAL_STAGES_PER_RUN}-"
                f"Sub {run_manager.current_substage_index}/{SUBSTAGES_PER_STAGE}: "
                f"{dungeon.biome.name}"
            )
        stage_surf = small_font.render(stage_str, False, COLOR_UI_TEXT)
        surface.blit(stage_surf, (tr_rect.x + 8, tr_rect.y + 7))

        all_stage_shrines = (
            run_manager.stage_shrines_activated >= REQUIRED_SHRINES_PER_STAGE_V2
        )
        shrine_col = (110, 235, 140) if all_stage_shrines else COLOR_UI_GOLD
        shrine_str = (
            f"Stage Shrines: {run_manager.stage_shrines_activated}/"
            f"{REQUIRED_SHRINES_PER_STAGE_V2}"
        )
        shrine_surf = small_font.render(shrine_str, False, shrine_col)
        surface.blit(shrine_surf, (tr_rect.x + 8, tr_rect.y + 26))

        self._render_minimap(surface, run_manager)

        # 3. Bottom-Left Panel: Skill Icons & Cooldown Indicators
        self._render_skill_bar(surface, run_manager, small_font)

        # 4. Top-Center Boss Health Bar (when Boss is engaged or player is in Boss room)
        boss = run_manager.boss
        px_tile, py_tile = player.tile_pos
        in_boss_room = dungeon.boss_room.contains_tile(px_tile, py_tile)
        if boss is not None and boss.alive and (boss.engaged or in_boss_room):
            boss_panel = pygame.Rect(INTERNAL_WIDTH // 2 - 140, 10, 280, 32)
            pygame.draw.rect(surface, COLOR_UI_PANEL, boss_panel)
            pygame.draw.rect(surface, COLOR_UI_BORDER, boss_panel, 1)

            b_name = small_font.render(boss.name, False, COLOR_UI_GOLD)
            surface.blit(
                b_name,
                (boss_panel.centerx - b_name.get_width() // 2, boss_panel.y + 4),
            )

            b_bar_bg = pygame.Rect(boss_panel.x + 10, boss_panel.y + 18, 260, 9)
            pygame.draw.rect(surface, COLOR_UI_HP_BG, b_bar_bg)
            b_ratio = max(0.0, min(1.0, boss.hp / max(1, boss.max_hp)))
            b_bar_fill = pygame.Rect(
                boss_panel.x + 10,
                boss_panel.y + 18,
                int(260 * b_ratio),
                9,
            )
            pygame.draw.rect(surface, COLOR_UI_BOSS_HP, b_bar_fill)
            pygame.draw.rect(surface, COLOR_UI_BORDER, b_bar_bg, 1)

        # 5. Interaction prompt & status banner
        if run_manager.status_banner_timer > 0.0 and run_manager.status_banner_text:
            banner_surf = small_font.render(run_manager.status_banner_text, False, COLOR_UI_GOLD)
            bw = banner_surf.get_width() + 16
            b_rect = pygame.Rect(INTERNAL_WIDTH // 2 - bw // 2, INTERNAL_HEIGHT - 64, bw, 20)
            pygame.draw.rect(surface, COLOR_UI_PANEL, b_rect)
            pygame.draw.rect(surface, COLOR_UI_BORDER, b_rect, 1)
            surface.blit(banner_surf, (b_rect.x + 8, b_rect.y + 4))

        nearby_shrine = shrine_sys.get_interactable_shrine(player.x, player.y)
        if nearby_shrine is not None:
            guarded = shrine_sys.is_shrine_guarded(nearby_shrine, run_manager.enemies)
            prompt_msg = (
                "Shrine Guarded! Defeat Room Enemies"
                if guarded
                else "Press [F] to Activate Shrine"
            )
            p_surf = small_font.render(prompt_msg, False, COLOR_UI_CRYSTAL)
            surface.blit(
                p_surf,
                (INTERNAL_WIDTH // 2 - p_surf.get_width() // 2, INTERNAL_HEIGHT - 38),
            )
        elif run_manager.portal is not None and run_manager.portal.is_player_in_range(
            player.x, player.y
        ):
            p_surf = small_font.render(
                "Press [F] to Enter Stage Portal",
                False,
                (190, 140, 255),
            )
            surface.blit(
                p_surf,
                (INTERNAL_WIDTH // 2 - p_surf.get_width() // 2, INTERNAL_HEIGHT - 38),
            )

    def _render_skill_bar(
        self,
        surface: pygame.Surface,
        run_manager: RunManager,
        small_font: pygame.font.Font,
    ) -> None:
        """Render skill slots at bottom-left with cooldown timers."""
        player = run_manager.player
        if player is None:
            return

        slots = [
            ("LMB", "Attack", True, player.attack_cooldown_timer),
            ("Q", "Skill 1", player.skill_1_unlocked, player.skill_1_cooldown_timer),
            ("E", "Skill 2", player.skill_2_unlocked, player.skill_2_cooldown_timer),
            ("SPC", "Dash", True, player.dash_cooldown_timer),
        ]

        start_x = 8
        y = INTERNAL_HEIGHT - 42
        slot_w = 54
        slot_h = 34

        for idx, (key_label, name, unlocked, cd_timer) in enumerate(slots):
            rect = pygame.Rect(start_x + idx * (slot_w + 5), y, slot_w, slot_h)
            bg = COLOR_UI_PANEL if unlocked else (20, 16, 26)
            pygame.draw.rect(surface, bg, rect)
            border = (
                COLOR_UI_GOLD
                if (unlocked and cd_timer <= 0.0)
                else COLOR_UI_BORDER
            )
            pygame.draw.rect(surface, border, rect, 1)

            k_surf = small_font.render(f"[{key_label}]", False, COLOR_UI_TEXT)
            surface.blit(k_surf, (rect.x + 4, rect.y + 3))

            if not unlocked:
                st_surf = small_font.render("LOCK", False, (170, 75, 80))
            elif cd_timer > 0.0:
                st_surf = small_font.render(f"{cd_timer:.1f}s", False, COLOR_UI_MUTED)
            else:
                st_surf = small_font.render(name, False, (130, 225, 145))
            surface.blit(st_surf, (rect.x + 4, rect.y + 18))

    def _render_minimap(self, surface: pygame.Surface, run_manager: RunManager) -> None:
        """Render a compact tactical dungeon minimap below the top-right stage panel."""
        dungeon = run_manager.dungeon
        player = run_manager.player
        shrine_sys = run_manager.shrine_system
        if dungeon is None or player is None or shrine_sys is None:
            return

        map_w = 78
        map_h = 78
        map_rect = pygame.Rect(INTERNAL_WIDTH - map_w - 8, 60, map_w, map_h)
        pygame.draw.rect(surface, (14, 12, 20), map_rect)
        pygame.draw.rect(surface, COLOR_UI_BORDER, map_rect, 1)

        scale_x = (map_w - 8) / max(1, dungeon.tilemap.width)
        scale_y = (map_h - 8) / max(1, dungeon.tilemap.height)
        ox = map_rect.x + 4
        oy = map_rect.y + 4

        # Draw corridor lines
        for corr in dungeon.corridors:
            sx, sy = corr.start_tile
            bx, by = corr.bend_tile
            ex, ey = corr.end_tile
            p1 = (int(ox + sx * scale_x), int(oy + sy * scale_y))
            p2 = (int(ox + bx * scale_x), int(oy + by * scale_y))
            p3 = (int(ox + ex * scale_x), int(oy + ey * scale_y))
            pygame.draw.lines(surface, (70, 62, 88), False, [p1, p2, p3], 1)

        # Draw rooms
        for room in dungeon.rooms:
            rx = int(ox + room.x * scale_x)
            ry = int(oy + room.y * scale_y)
            rw = max(3, int(room.width * scale_x))
            rh = max(3, int(room.height * scale_y))
            col = (85, 78, 108)
            if room.room_type == RoomType.ENTRANCE:
                col = (90, 185, 110)
            elif room.room_type == RoomType.BOSS:
                col = (210, 55, 65)
            elif room.room_type == RoomType.SHRINE:
                col = (80, 175, 240)
            elif room.room_type in (RoomType.CHEST, RoomType.TREASURE, RoomType.SHOP):
                col = (225, 185, 75)
            elif room.room_type == RoomType.SPECIAL:
                col = (165, 110, 225)
            elif room.is_mandatory:
                col = (135, 95, 130)
            pygame.draw.rect(surface, col, pygame.Rect(rx, ry, rw, rh))

        # Draw player dot
        ptx, pty = player.tile_pos
        px = int(ox + ptx * scale_x)
        py = int(oy + pty * scale_y)
        pygame.draw.rect(surface, (255, 245, 130), pygame.Rect(px - 1, py - 1, 3, 3))
