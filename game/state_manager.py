"""Finite state manager for top-level game screens."""

from __future__ import annotations

from enum import Enum


class GameState(Enum):
    """High-level application states for THE FRACTURED GATE."""

    MAIN_MENU = "main_menu"
    HUB_ROOM = "hub_room"
    CHARACTER_SELECTION = "character_selection"
    GAMEPLAY = "gameplay"
    PAUSED = "paused"
    TREASURE_ROOM = "treasure_room"
    VICTORY = "victory"
    GAME_OVER = "game_over"


class StateManager:
    """Tracks current and previous GameState transitions."""

    def __init__(self, initial_state: GameState = GameState.MAIN_MENU) -> None:
        self.current_state: GameState = initial_state
        self.previous_state: GameState = initial_state

    def change_state(self, new_state: GameState) -> None:
        """Transition to new_state and record previous_state."""
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state

    def transition_to_hub_room(self) -> None:
        """Transition to the Hub Room state (replaces Character Selection in Revision 2.0)."""
        self.change_state(GameState.HUB_ROOM)
