"""Core application, rendering, and palette settings for THE FRACTURED GATE."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_base_path() -> Path:
    """Return base path supporting both normal execution and PyInstaller bundles."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


BASE_DIR: Path = get_base_path()
ASSETS_DIR: Path = BASE_DIR / "assets"
SAVE_DIR: Path = Path(os.environ.get("TFG_SAVE_DIR", str(BASE_DIR / "saves")))
SAVE_FILE_PATH: Path = SAVE_DIR / "profile.save.json"
SAVE_BACKUP_PATH: Path = SAVE_DIR / "profile.save.bak"

GAME_TITLE: str = "THE FRACTURED GATE"
GAME_VERSION: str = "0.1.0-phase1"

# Rendering & Display
INTERNAL_WIDTH: int = 640
INTERNAL_HEIGHT: int = 360
INTERNAL_RESOLUTION: tuple[int, int] = (INTERNAL_WIDTH, INTERNAL_HEIGHT)

WINDOW_SCALE: int = 2
WINDOW_WIDTH: int = INTERNAL_WIDTH * WINDOW_SCALE
WINDOW_HEIGHT: int = INTERNAL_HEIGHT * WINDOW_SCALE
WINDOW_RESOLUTION: tuple[int, int] = (WINDOW_WIDTH, WINDOW_HEIGHT)

TARGET_FPS: int = 60
TILE_SIZE: int = 16

# Dark Fantasy Medieval Color Palette (RGB / RGBA)
COLOR_BG_VOID: tuple[int, int, int] = (10, 8, 14)
COLOR_FLOOR_PRIMARY: tuple[int, int, int] = (34, 30, 42)
COLOR_FLOOR_ACCENT: tuple[int, int, int] = (42, 37, 52)
COLOR_CORRIDOR_FLOOR: tuple[int, int, int] = (29, 26, 36)
COLOR_WALL_TOP: tuple[int, int, int] = (20, 17, 27)
COLOR_WALL_FRONT: tuple[int, int, int] = (54, 46, 68)
COLOR_WALL_BORDER: tuple[int, int, int] = (76, 65, 94)
COLOR_DOOR_LOCKED: tuple[int, int, int] = (140, 35, 45)
COLOR_DOOR_UNLOCKED: tuple[int, int, int] = (70, 155, 95)

# Entity & Objective Colors
COLOR_PLAYER_WARRIOR: tuple[int, int, int] = (210, 175, 95)
COLOR_PLAYER_MAGE: tuple[int, int, int] = (95, 155, 235)
COLOR_PLAYER_ARCHER: tuple[int, int, int] = (95, 195, 115)
COLOR_PLAYER_DASH: tuple[int, int, int] = (245, 235, 190)

COLOR_ENEMY_MELEE: tuple[int, int, int] = (175, 55, 60)
COLOR_ENEMY_RANGED: tuple[int, int, int] = (155, 70, 185)
COLOR_ENEMY_FAST: tuple[int, int, int] = (215, 120, 50)
COLOR_ENEMY_ELITE: tuple[int, int, int] = (200, 35, 90)
COLOR_BOSS: tuple[int, int, int] = (230, 30, 45)

COLOR_SHRINE_INACTIVE: tuple[int, int, int] = (70, 165, 235)
COLOR_SHRINE_ACTIVE: tuple[int, int, int] = (240, 200, 80)
COLOR_TREASURE_CHEST: tuple[int, int, int] = (230, 180, 45)
COLOR_PORTAL: tuple[int, int, int] = (150, 80, 240)

# UI Colors
COLOR_UI_BG: tuple[int, int, int] = (18, 15, 24)
COLOR_UI_PANEL: tuple[int, int, int] = (28, 24, 38)
COLOR_UI_BORDER: tuple[int, int, int] = (98, 84, 122)
COLOR_UI_TEXT: tuple[int, int, int] = (230, 224, 238)
COLOR_UI_MUTED: tuple[int, int, int] = (145, 136, 160)
COLOR_UI_GOLD: tuple[int, int, int] = (240, 195, 65)
COLOR_UI_CRYSTAL: tuple[int, int, int] = (80, 185, 250)
COLOR_UI_HP_FILL: tuple[int, int, int] = (185, 40, 50)
COLOR_UI_HP_BG: tuple[int, int, int] = (55, 20, 28)
COLOR_UI_BOSS_HP: tuple[int, int, int] = (210, 35, 75)
