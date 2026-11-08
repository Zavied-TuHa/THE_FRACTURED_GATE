"""Delta-time AnimationController with 4 directions, 8-frame clips, events, and priority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable
import pygame


class Direction(Enum):
    """Four cardinal facing directions for top-down 2D sprites."""

    DOWN = "down"
    UP = "up"
    LEFT = "left"
    RIGHT = "right"

    @classmethod
    def from_vector(
        cls,
        dx: float,
        dy: float,
        fallback: Direction | None = None,
    ) -> Direction:
        """Convert a 2D directional vector (dx, dy) into one of the four cardinal directions."""
        if abs(dx) < 1e-4 and abs(dy) < 1e-4:
            return fallback if fallback is not None else cls.DOWN
        if abs(dx) >= abs(dy):
            return cls.RIGHT if dx >= 0.0 else cls.LEFT
        return cls.DOWN if dy >= 0.0 else cls.UP


class AnimationState(Enum):
    """Required character animation states under the Official Art Direction Lock."""

    IDLE = "idle"
    WALK = "walk"
    ATTACK = "attack"
    SKILL_1 = "skill_1"
    SKILL_2 = "skill_2"
    HURT = "hurt"
    DEATH = "death"


# Priority hierarchy: Death MUST have the highest animation priority.
ANIMATION_PRIORITY: dict[AnimationState, int] = {
    AnimationState.IDLE: 10,
    AnimationState.WALK: 20,
    AnimationState.ATTACK: 50,
    AnimationState.SKILL_1: 60,
    AnimationState.SKILL_2: 65,
    AnimationState.HURT: 80,
    AnimationState.DEATH: 100,
}


@dataclass
class AnimationClip:
    """Directional animation clip supporting looping, one-shot playback, and frame events."""

    state: AnimationState
    frames_by_direction: dict[Direction, list[pygame.Surface]]
    frame_duration: float = 0.08
    loop: bool = True
    events: dict[int, str] = field(default_factory=dict)

    @property
    def frame_count(self) -> int:
        """Return number of frames in the clip (targets 8 frames for standard animations)."""
        for frames in self.frames_by_direction.values():
            return len(frames)
        return 0

    def get_frame(self, direction: Direction, index: int) -> pygame.Surface:
        """Return the surface for the requested direction and clamped frame index."""
        frames = self.frames_by_direction.get(direction)
        if not frames:
            frames = next(iter(self.frames_by_direction.values()))
        safe_idx = max(0, min(len(frames) - 1, index))
        return frames[safe_idx]


AnimationEventCallback = Callable[[str], None]


class AnimationController:
    """Manages state transitions, 4-direction selection, delta-time stepping, and events."""

    def __init__(
        self,
        clips: dict[AnimationState, AnimationClip],
        initial_state: AnimationState = AnimationState.IDLE,
        initial_direction: Direction = Direction.DOWN,
    ) -> None:
        self.clips: dict[AnimationState, AnimationClip] = clips
        self.state: AnimationState = initial_state
        self.direction: Direction = initial_direction
        self.frame_index: int = 0
        self.frame_timer: float = 0.0
        self.finished: bool = False
        self._fired_frames_in_cycle: set[int] = set()
        self._event_listeners: list[AnimationEventCallback] = []

    @property
    def priority(self) -> int:
        """Return priority of the currently active animation state."""
        return ANIMATION_PRIORITY[self.state]

    def register_event_listener(self, callback: AnimationEventCallback) -> None:
        """Register a listener invoked whenever an animation frame event triggers."""
        if callback not in self._event_listeners:
            self._event_listeners.append(callback)

    def set_direction(self, direction: Direction) -> None:
        """Update facing direction unless locked in DEATH state."""
        if self.state == AnimationState.DEATH:
            return
        self.direction = direction

    def set_direction_from_vector(self, dx: float, dy: float) -> None:
        """Update facing direction from a 2D vector unless locked in DEATH state."""
        if self.state == AnimationState.DEATH:
            return
        self.direction = Direction.from_vector(dx, dy, fallback=self.direction)

    def play(
        self,
        new_state: AnimationState,
        direction: Direction | None = None,
        restart_if_same: bool = False,
    ) -> bool:
        """Request transition to new_state respecting priority rules.

        Returns True if the state was changed or restarted.
        """
        if new_state not in self.clips:
            return False

        # Death has highest priority and cannot be overridden once started
        if self.state == AnimationState.DEATH and new_state != AnimationState.DEATH:
            return False

        new_priority = ANIMATION_PRIORITY[new_state]
        current_clip = self.clips[self.state]

        # If current clip is an active (un-finished) one-shot animation,
        # only allow states with strictly higher or equal priority (e.g., HURT or DEATH)
        if not current_clip.loop and not self.finished:
            if new_state == self.state and not restart_if_same:
                return False
            if new_priority < self.priority:
                return False

        if direction is not None and self.state != AnimationState.DEATH:
            self.direction = direction

        if self.state == new_state and not restart_if_same and not self.finished:
            return False

        self.state = new_state
        self.frame_index = 0
        self.frame_timer = 0.0
        self.finished = False
        self._fired_frames_in_cycle.clear()
        return True

    def force_reset(
        self,
        state: AnimationState = AnimationState.IDLE,
        direction: Direction = Direction.DOWN,
    ) -> None:
        """Explicitly reset controller state (e.g., when starting a new run)."""
        self.state = state
        self.direction = direction
        self.frame_index = 0
        self.frame_timer = 0.0
        self.finished = False
        self._fired_frames_in_cycle.clear()

    def update(self, dt: float) -> list[str]:
        """Advance animation using delta-time and return any frame events triggered."""
        clip = self.clips[self.state]
        total_frames = clip.frame_count
        if total_frames <= 0:
            return []

        triggered_events: list[str] = []

        # Fire frame 0 event if present and not yet fired in this cycle
        self._check_and_fire_frame_event(clip, self.frame_index, triggered_events)

        if self.finished and not clip.loop:
            return triggered_events

        self.frame_timer += max(0.0, dt)
        frame_dur = max(0.001, clip.frame_duration)

        while self.frame_timer >= frame_dur:
            self.frame_timer -= frame_dur
            next_index = self.frame_index + 1

            if next_index < total_frames:
                self.frame_index = next_index
                self._check_and_fire_frame_event(clip, self.frame_index, triggered_events)
            else:
                if clip.loop:
                    self.frame_index = 0
                    self._fired_frames_in_cycle.clear()
                    self._check_and_fire_frame_event(
                        clip, self.frame_index, triggered_events
                    )
                else:
                    self.frame_index = total_frames - 1
                    self.finished = True
                    self.frame_timer = 0.0
                    break

        # Automatically fall back from completed non-death one-shot animations to IDLE
        if self.finished and not clip.loop and self.state != AnimationState.DEATH:
            self.state = AnimationState.IDLE
            self.frame_index = 0
            self.frame_timer = 0.0
            self.finished = False
            self._fired_frames_in_cycle.clear()

        return triggered_events

    def _check_and_fire_frame_event(
        self,
        clip: AnimationClip,
        frame_idx: int,
        out_events: list[str],
    ) -> None:
        """Check if clip defines an event on frame_idx and dispatch it once per cycle."""
        if frame_idx in self._fired_frames_in_cycle:
            return
        event_name = clip.events.get(frame_idx)
        if event_name:
            self._fired_frames_in_cycle.add(frame_idx)
            out_events.append(event_name)
            for listener in self._event_listeners:
                listener(event_name)

    def get_current_frame(self) -> pygame.Surface:
        """Return the current directional frame Surface for blitting."""
        clip = self.clips[self.state]
        return clip.get_frame(self.direction, self.frame_index)
