"""AssetManager for loading, caching, slicing, and synthesizing transparent PNG assets."""

from __future__ import annotations

import math
from pathlib import Path
import pygame

from config.settings import (
    ASSETS_DIR,
    SPRITE_SIZE_CHARACTER,
    SPRITE_SIZE_WEAPON,
    STANDARD_ANIMATION_FRAMES,
    TILE_SIZE,
)
from systems.animation import (
    AnimationClip,
    AnimationController,
    AnimationState,
    Direction,
)
from world.biome import BIOMES, BiomeConfig


DIRECTION_ORDER: tuple[Direction, ...] = (
    Direction.DOWN,
    Direction.UP,
    Direction.LEFT,
    Direction.RIGHT,
)

STATE_ORDER: tuple[AnimationState, ...] = (
    AnimationState.IDLE,
    AnimationState.WALK,
    AnimationState.ATTACK,
    AnimationState.SKILL_1,
    AnimationState.SKILL_2,
    AnimationState.HURT,
    AnimationState.DEATH,
)


class AssetManager:
    """Centralized loader and cache for transparent PNG spritesheets and biome tilesets."""

    _instance: AssetManager | None = None

    def __init__(self, assets_dir: Path = ASSETS_DIR) -> None:
        self.assets_dir: Path = assets_dir
        self.sprites_dir: Path = self.assets_dir / "sprites"
        self.tilesets_dir: Path = self.assets_dir / "tilesets"
        self._surface_cache: dict[str, pygame.Surface] = {}
        self._tileset_cache: dict[str, dict[str, list[pygame.Surface]]] = {}

        self.sprites_dir.mkdir(parents=True, exist_ok=True)
        self.tilesets_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_phase2_1_assets()

    @classmethod
    def get_instance(cls) -> AssetManager:
        """Return the singleton AssetManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ensure_phase2_1_assets(self) -> None:
        """Ensure Warrior Chibi 32x32 PNG spritesheet, 16x16 weapon, and 3 biome tilesets exist."""
        warrior_sheet_path = self.sprites_dir / "warrior_chibi_32x32.png"
        if not warrior_sheet_path.exists():
            sheet = self._generate_warrior_chibi_spritesheet()
            pygame.image.save(sheet, str(warrior_sheet_path))

        weapon_path = self.sprites_dir / "warrior_sword_16x16.png"
        if not weapon_path.exists():
            weapon_surf = self._generate_warrior_weapon_sprite()
            pygame.image.save(weapon_surf, str(weapon_path))

        for biome_id, biome_cfg in BIOMES.items():
            tileset_path = self.tilesets_dir / f"{biome_id}.png"
            if not tileset_path.exists():
                ts_surf = self._generate_biome_tileset_png(biome_cfg)
                pygame.image.save(ts_surf, str(tileset_path))

    def load_png(self, relative_path: str) -> pygame.Surface:
        """Load and cache a transparent PNG surface without anti-aliased filtering."""
        if relative_path in self._surface_cache:
            return self._surface_cache[relative_path]

        full_path = self.assets_dir / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"Asset file not found: {full_path}")

        loaded = pygame.image.load(str(full_path))
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            loaded = loaded.convert_alpha()
        else:
            alpha_surf = pygame.Surface(loaded.get_size(), pygame.SRCALPHA)
            alpha_surf.blit(loaded, (0, 0))
            loaded = alpha_surf

        self._surface_cache[relative_path] = loaded
        return loaded

    def slice_grid(
        self,
        sheet: pygame.Surface,
        frame_width: int,
        frame_height: int,
    ) -> list[list[pygame.Surface]]:
        """Slice a spritesheet Surface into a 2D [row][col] list of transparent sub-surfaces."""
        sheet_w, sheet_h = sheet.get_size()
        cols = sheet_w // frame_width
        rows = sheet_h // frame_height
        grid: list[list[pygame.Surface]] = []

        for r in range(rows):
            row_frames: list[pygame.Surface] = []
            for c in range(cols):
                frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
                source_rect = pygame.Rect(
                    c * frame_width,
                    r * frame_height,
                    frame_width,
                    frame_height,
                )
                frame.blit(sheet, (0, 0), source_rect)
                row_frames.append(frame)
            grid.append(row_frames)
        return grid

    def create_character_animation_controller(
        self,
        character_id: str = "warrior",
    ) -> AnimationController:
        """Build a 4-direction, 8-frame AnimationController for a playable character."""
        # Phase 2.1 uses warrior_chibi_32x32.png as the canonical integration example
        sheet_rel = f"sprites/{character_id}_chibi_32x32.png"
        if not (self.assets_dir / sheet_rel).exists():
            sheet_rel = "sprites/warrior_chibi_32x32.png"

        sheet = self.load_png(sheet_rel)
        fw, fh = SPRITE_SIZE_CHARACTER
        grid = self.slice_grid(sheet, fw, fh)

        clip_configs: dict[AnimationState, tuple[float, bool, dict[int, str]]] = {
            AnimationState.IDLE: (0.10, True, {}),
            AnimationState.WALK: (0.075, True, {2: "footstep", 6: "footstep"}),
            AnimationState.ATTACK: (0.045, False, {3: "attack_hit"}),
            AnimationState.SKILL_1: (0.055, False, {3: "skill_1_hit"}),
            AnimationState.SKILL_2: (0.060, False, {4: "skill_2_hit"}),
            AnimationState.HURT: (0.050, False, {1: "hurt_recoil"}),
            AnimationState.DEATH: (0.085, False, {7: "death_complete"}),
        }

        clips: dict[AnimationState, AnimationClip] = {}
        for state_idx, state in enumerate(STATE_ORDER):
            frames_by_dir: dict[Direction, list[pygame.Surface]] = {}
            for dir_idx, direction in enumerate(DIRECTION_ORDER):
                row_index = state_idx * len(DIRECTION_ORDER) + dir_idx
                frames_by_dir[direction] = grid[row_index][:STANDARD_ANIMATION_FRAMES]

            frame_dur, loop_flag, events_map = clip_configs[state]
            clips[state] = AnimationClip(
                state=state,
                frames_by_direction=frames_by_dir,
                frame_duration=frame_dur,
                loop=loop_flag,
                events=dict(events_map),
            )

        return AnimationController(clips=clips)

    def get_biome_tileset(self, biome_id: str) -> dict[str, list[pygame.Surface]]:
        """Load and slice a biome's 16x16 PNG tileset into layer tile lists."""
        if biome_id in self._tileset_cache:
            return self._tileset_cache[biome_id]

        rel_path = f"tilesets/{biome_id}.png"
        if not (self.assets_dir / rel_path).exists():
            rel_path = "tilesets/enchanted_forest.png"

        sheet = self.load_png(rel_path)
        row = self.slice_grid(sheet, TILE_SIZE, TILE_SIZE)[0]

        parsed = {
            "ground": row[0:3],       # floor_primary, floor_accent, corridor
            "decoration": row[3:6],   # subtle biome floor details (transparent PNG)
            "wall": row[6:9],         # wall_front, boss_gate_locked, boss_gate_unlocked
            "foreground": row[9:11],  # upper wall crown / parapet overlay
        }
        self._tileset_cache[biome_id] = parsed
        return parsed

    def _generate_warrior_weapon_sprite(self) -> pygame.Surface:
        """Synthesize a 16x16 Chibi broadsword PNG with dark outline and flat shading."""
        w, h = SPRITE_SIZE_WEAPON
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        outline = (18, 14, 24, 255)
        blade_light = (225, 232, 245, 255)
        blade_dark = (155, 165, 188, 255)
        hilt_gold = (235, 185, 65, 255)
        grip_red = (155, 42, 52, 255)

        # Blade outline & core
        pygame.draw.rect(surf, outline, pygame.Rect(5, 1, 6, 10))
        pygame.draw.rect(surf, blade_light, pygame.Rect(6, 2, 2, 8))
        pygame.draw.rect(surf, blade_dark, pygame.Rect(8, 2, 2, 8))
        # Crossguard
        pygame.draw.rect(surf, outline, pygame.Rect(3, 10, 10, 3))
        pygame.draw.rect(surf, hilt_gold, pygame.Rect(4, 11, 8, 1))
        # Grip & Pommel
        pygame.draw.rect(surf, outline, pygame.Rect(6, 12, 4, 4))
        pygame.draw.rect(surf, grip_red, pygame.Rect(7, 12, 2, 2))
        pygame.draw.rect(surf, hilt_gold, pygame.Rect(7, 14, 2, 1))
        return surf

    def _generate_warrior_chibi_spritesheet(self) -> pygame.Surface:
        """Generate a 28-row x 8-column (256x896) 32x32 Chibi Warrior PNG spritesheet."""
        fw, fh = SPRITE_SIZE_CHARACTER
        cols = STANDARD_ANIMATION_FRAMES
        rows = len(STATE_ORDER) * len(DIRECTION_ORDER)
        sheet = pygame.Surface((cols * fw, rows * fh), pygame.SRCALPHA)
        sheet.fill((0, 0, 0, 0))

        for state_idx, state in enumerate(STATE_ORDER):
            for dir_idx, direction in enumerate(DIRECTION_ORDER):
                row_idx = state_idx * len(DIRECTION_ORDER) + dir_idx
                for frame_idx in range(cols):
                    cell = pygame.Surface((fw, fh), pygame.SRCALPHA)
                    cell.fill((0, 0, 0, 0))
                    self._draw_chibi_warrior_frame(cell, state, direction, frame_idx)
                    sheet.blit(cell, (frame_idx * fw, row_idx * fh))

        return sheet

    def _draw_chibi_warrior_frame(
        self,
        surf: pygame.Surface,
        state: AnimationState,
        direction: Direction,
        frame_idx: int,
    ) -> None:
        """Draw a single 32x32 Chibi Pixel-Art Warrior frame (Soul Knight proportions)."""
        # Palette: Dark outline, flat steel/gold shading, crimson cape
        outline = (16, 12, 22, 255)
        helm_main = (142, 152, 175, 255)
        helm_shade = (96, 104, 126, 255)
        gold_trim = (238, 190, 72, 255)
        plume_red = (205, 48, 62, 255)
        cape_red = (168, 36, 52, 255)
        armor_chest = (118, 126, 148, 255)
        boot_dark = (48, 42, 58, 255)
        eye_glow = (250, 225, 110, 255)
        blade_col = (230, 238, 250, 255)

        if state == AnimationState.HURT and frame_idx in (1, 2, 3):
            helm_main = (250, 235, 235, 255)
            armor_chest = (245, 190, 190, 255)

        # Bobbing and stride offsets across 8 frames
        phase = (frame_idx / float(STANDARD_ANIMATION_FRAMES)) * math.pi * 2.0
        bob_y = 0
        stride_l = 0
        stride_r = 0

        if state == AnimationState.IDLE:
            bob_y = -1 if frame_idx in (2, 3, 4) else 0
        elif state == AnimationState.WALK:
            bob_y = -1 if frame_idx % 4 in (1, 2) else 0
            stride_l = int(round(math.sin(phase) * 2))
            stride_r = -stride_l
        elif state == AnimationState.HURT:
            bob_y = -1 if frame_idx < 4 else 0

        cx, cy = 16, 18 + bob_y

        # Handle DEATH animation collapse (frames 0..7)
        if state == AnimationState.DEATH:
            drop = min(7, frame_idx)
            cy = 18 + drop // 2
            if frame_idx >= 5:
                # Fallen chibi knight silhouette on the ground
                pygame.draw.rect(surf, outline, pygame.Rect(6, 22, 20, 8))
                pygame.draw.rect(surf, cape_red, pygame.Rect(7, 23, 18, 6))
                pygame.draw.rect(surf, helm_main, pygame.Rect(9, 21, 10, 6))
                pygame.draw.rect(surf, outline, pygame.Rect(9, 21, 10, 6), 1)
                pygame.draw.rect(surf, gold_trim, pygame.Rect(12, 20, 4, 2))
                return

        # 1. Cape behind character when facing DOWN, LEFT, or RIGHT
        if direction != Direction.UP:
            cape_rect = pygame.Rect(cx - 7, cy - 1, 14, 9)
            pygame.draw.rect(surf, outline, cape_rect)
            pygame.draw.rect(surf, cape_red, cape_rect.inflate(-2, -2))

        # 2. Chibi Boots (foot position at y=28..30 inside 32x32 frame)
        left_foot = pygame.Rect(cx - 5, 26 + stride_l, 4, 4)
        right_foot = pygame.Rect(cx + 1, 26 + stride_r, 4, 4)
        pygame.draw.rect(surf, outline, left_foot.inflate(2, 2))
        pygame.draw.rect(surf, boot_dark, left_foot)
        pygame.draw.rect(surf, outline, right_foot.inflate(2, 2))
        pygame.draw.rect(surf, boot_dark, right_foot)

        # 3. Compact Chibi Armored Torso
        torso_rect = pygame.Rect(cx - 6, cy, 12, 8)
        pygame.draw.rect(surf, outline, torso_rect.inflate(2, 2))
        pygame.draw.rect(surf, armor_chest, torso_rect)
        pygame.draw.rect(surf, gold_trim, pygame.Rect(cx - 5, cy + 5, 10, 2))

        # When facing UP, draw cape over the back of torso
        if direction == Direction.UP:
            back_cape = pygame.Rect(cx - 6, cy, 12, 8)
            pygame.draw.rect(surf, outline, back_cape.inflate(2, 2))
            pygame.draw.rect(surf, cape_red, back_cape)

        # 4. Oversized Chibi Head / Knight Helmet (14x12)
        head_rect = pygame.Rect(cx - 7, cy - 10, 14, 11)
        pygame.draw.rect(surf, outline, head_rect.inflate(2, 2))
        pygame.draw.rect(surf, helm_main, head_rect)
        pygame.draw.rect(surf, helm_shade, pygame.Rect(cx - 7, cy - 3, 14, 4))

        # Helmet Plume & Gold Crest
        plume_rect = pygame.Rect(cx - 2, cy - 14, 4, 4)
        pygame.draw.rect(surf, outline, plume_rect.inflate(2, 2))
        pygame.draw.rect(surf, plume_red, plume_rect)
        pygame.draw.rect(surf, gold_trim, pygame.Rect(cx - 4, cy - 10, 8, 2))

        # Directional Visor & Glowing Eyes
        if direction == Direction.DOWN:
            pygame.draw.rect(surf, outline, pygame.Rect(cx - 5, cy - 5, 10, 4))
            pygame.draw.rect(surf, eye_glow, pygame.Rect(cx - 4, cy - 4, 2, 2))
            pygame.draw.rect(surf, eye_glow, pygame.Rect(cx + 2, cy - 4, 2, 2))
        elif direction == Direction.LEFT:
            pygame.draw.rect(surf, outline, pygame.Rect(cx - 7, cy - 5, 6, 4))
            pygame.draw.rect(surf, eye_glow, pygame.Rect(cx - 6, cy - 4, 2, 2))
        elif direction == Direction.RIGHT:
            pygame.draw.rect(surf, outline, pygame.Rect(cx + 1, cy - 5, 6, 4))
            pygame.draw.rect(surf, eye_glow, pygame.Rect(cx + 4, cy - 4, 2, 2))

        # 5. Weapon & Combat Swing Animations (Attack, Skill 1, Skill 2)
        self._draw_warrior_weapon_for_state(
            surf, cx, cy, state, direction, frame_idx, outline, blade_col, gold_trim
        )

    def _draw_warrior_weapon_for_state(
        self,
        surf: pygame.Surface,
        cx: int,
        cy: int,
        state: AnimationState,
        direction: Direction,
        frame_idx: int,
        outline: tuple[int, int, int, int],
        blade_col: tuple[int, int, int, int],
        gold_trim: tuple[int, int, int, int],
    ) -> None:
        """Render the Warrior's broadsword and skill aura across frames."""
        if state in (AnimationState.ATTACK, AnimationState.SKILL_1, AnimationState.SKILL_2):
            # Dynamic swing arc across the 8 frames
            swing_angles = (-65, -40, -10, 25, 55, 70, 45, 15)
            base_dir_angle = {
                Direction.RIGHT: 0.0,
                Direction.DOWN: 90.0,
                Direction.LEFT: 180.0,
                Direction.UP: -90.0,
            }[direction]

            if state == AnimationState.SKILL_2:
                # 360-degree Iron Tempest spin
                ang_rad = math.radians(frame_idx * 45.0)
            else:
                ang_rad = math.radians(base_dir_angle + swing_angles[frame_idx])

            wx = int(round(cx + math.cos(ang_rad) * 11))
            wy = int(round(cy + 2 + math.sin(ang_rad) * 11))
            hx = int(round(cx + math.cos(ang_rad) * 5))
            hy = int(round(cy + 2 + math.sin(ang_rad) * 5))

            pygame.draw.line(surf, outline, (hx, hy), (wx, wy), 5)
            sword_tint = (
                (255, 145, 85, 255)
                if state == AnimationState.SKILL_1
                else (
                    (255, 215, 95, 255)
                    if state == AnimationState.SKILL_2
                    else blade_col
                )
            )
            pygame.draw.line(surf, sword_tint, (hx, hy), (wx, wy), 3)
            pygame.draw.rect(surf, gold_trim, pygame.Rect(hx - 1, hy - 1, 3, 3))
        else:
            # Idle/Walk resting sword at side
            sx = cx + (7 if direction != Direction.LEFT else -9)
            sy = cy - 2
            pygame.draw.rect(surf, outline, pygame.Rect(sx - 1, sy - 4, 4, 11))
            pygame.draw.rect(surf, blade_col, pygame.Rect(sx, sy - 3, 2, 7))
            pygame.draw.rect(surf, gold_trim, pygame.Rect(sx - 1, sy + 3, 4, 2))

    def _generate_biome_tileset_png(self, biome: BiomeConfig) -> pygame.Surface:
        """Synthesize an 11-tile (176x16) 16x16 pixel-art tileset PNG for a biome."""
        num_tiles = 11
        surf = pygame.Surface((num_tiles * TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        outline = (16, 12, 22, 255)

        # Tile 0: Ground Floor Primary
        t0 = pygame.Rect(0 * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surf, biome.floor_color, t0)
        pygame.draw.rect(surf, biome.floor_accent_color, pygame.Rect(2, 2, 3, 3))
        pygame.draw.rect(surf, biome.floor_accent_color, pygame.Rect(11, 9, 3, 3))

        # Tile 1: Ground Floor Accent
        t1 = pygame.Rect(1 * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surf, biome.floor_accent_color, t1)
        pygame.draw.rect(surf, biome.floor_color, pygame.Rect(1 * TILE_SIZE + 4, 5, 4, 3))
        pygame.draw.rect(surf, biome.floor_color, pygame.Rect(1 * TILE_SIZE + 10, 11, 3, 2))

        # Tile 2: Corridor Cobblestone
        t2 = pygame.Rect(2 * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surf, biome.corridor_color, t2)
        pygame.draw.rect(surf, biome.floor_color, pygame.Rect(2 * TILE_SIZE + 2, 3, 5, 4))
        pygame.draw.rect(surf, biome.floor_color, pygame.Rect(2 * TILE_SIZE + 9, 9, 5, 4))

        # Tiles 3..5: Decoration overlays (transparent background)
        dec_colors = {
            "enchanted_forest": (64, 138, 78, 220),
            "crystal_cavern": (95, 195, 245, 220),
            "demon_castle": (165, 45, 62, 220),
        }
        dec_col = dec_colors.get(biome.biome_id, (90, 140, 100, 220))
        # Tile 3: Moss / Crystal cluster / Runic crack
        ox3 = 3 * TILE_SIZE
        pygame.draw.rect(surf, outline, pygame.Rect(ox3 + 4, 5, 6, 5))
        pygame.draw.rect(surf, dec_col, pygame.Rect(ox3 + 5, 6, 4, 3))
        # Tile 4: Pebbles / Shards
        ox4 = 4 * TILE_SIZE
        pygame.draw.rect(surf, dec_col, pygame.Rect(ox4 + 3, 10, 3, 3))
        pygame.draw.rect(surf, dec_col, pygame.Rect(ox4 + 10, 4, 3, 3))
        # Tile 5: Ancient floor rune mark
        ox5 = 5 * TILE_SIZE
        pygame.draw.rect(surf, dec_col, pygame.Rect(ox5 + 6, 3, 4, 10), 1)

        # Tile 6: Wall Base Front (brick work + dark outline)
        ox6 = 6 * TILE_SIZE
        t6 = pygame.Rect(ox6, 0, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surf, biome.wall_top_color, t6)
        pygame.draw.rect(surf, biome.wall_front_color, pygame.Rect(ox6, 5, TILE_SIZE, 11))
        pygame.draw.line(surf, outline, (ox6, 5), (ox6 + TILE_SIZE - 1, 5), 1)
        pygame.draw.line(surf, outline, (ox6, 10), (ox6 + TILE_SIZE - 1, 10), 1)
        pygame.draw.line(surf, outline, (ox6 + 8, 5), (ox6 + 8, 10), 1)
        pygame.draw.rect(surf, outline, t6, 1)

        # Tile 7: Boss Gate Locked
        ox7 = 7 * TILE_SIZE
        t7 = pygame.Rect(ox7, 0, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surf, (135, 32, 44), t7)
        pygame.draw.rect(surf, (230, 85, 95), t7, 2)
        pygame.draw.rect(surf, outline, t7, 1)

        # Tile 8: Boss Gate Unlocked
        ox8 = 8 * TILE_SIZE
        t8 = pygame.Rect(ox8, 0, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surf, (58, 145, 85), t8)
        pygame.draw.rect(surf, (135, 230, 160), t8, 2)
        pygame.draw.rect(surf, outline, t8, 1)

        # Tile 9 & 10: Foreground Parapet / Upper Wall Crown (rendered over Y-sorted entities)
        ox9 = 9 * TILE_SIZE
        pygame.draw.rect(surf, biome.wall_top_color, pygame.Rect(ox9, 10, TILE_SIZE, 6))
        pygame.draw.rect(surf, outline, pygame.Rect(ox9, 10, TILE_SIZE, 6), 1)

        ox10 = 10 * TILE_SIZE
        pygame.draw.rect(surf, biome.wall_front_color, pygame.Rect(ox10 + 2, 11, 12, 5))
        pygame.draw.rect(surf, outline, pygame.Rect(ox10 + 2, 11, 12, 5), 1)

        return surf
