"""Player control bindings for keyboard and mouse."""

from __future__ import annotations

import pygame

KEY_MOVE_UP: tuple[int, ...] = (pygame.K_w, pygame.K_UP)
KEY_MOVE_DOWN: tuple[int, ...] = (pygame.K_s, pygame.K_DOWN)
KEY_MOVE_LEFT: tuple[int, ...] = (pygame.K_a, pygame.K_LEFT)
KEY_MOVE_RIGHT: tuple[int, ...] = (pygame.K_d, pygame.K_RIGHT)

MOUSE_BASIC_ATTACK: int = 1  # Left Mouse Button

KEY_SKILL_1: int = pygame.K_q
KEY_SKILL_2: int = pygame.K_e
KEY_DASH: int = pygame.K_SPACE
KEY_INTERACT: int = pygame.K_f
KEY_PAUSE: int = pygame.K_ESCAPE
