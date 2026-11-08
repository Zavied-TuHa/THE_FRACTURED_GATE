"""Entry point for THE FRACTURED GATE."""

from __future__ import annotations

import argparse
import sys

from game.game import FracturedGateGame


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse optional CLI flags for seed testing or headless smoke checks."""
    parser = argparse.ArgumentParser(description="THE FRACTURED GATE - 2D Action Roguelike")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening an OS window (for automated smoke tests).",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Automatically exit after rendering N frames.",
    )
    parser.add_argument(
        "--quick-start",
        action="store_true",
        help="Launch directly into a Warrior dungeon run.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Specify a deterministic run seed when using --quick-start.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Initialize and run THE FRACTURED GATE."""
    args = parse_args(argv)
    app = FracturedGateGame(headless=args.headless)

    if args.quick_start:
        from game.state_manager import GameState

        app.run_manager.start_new_run(character_id="warrior", seed=args.seed)
        if app.run_manager.player is not None:
            app.camera.snap_to(app.run_manager.player.x, app.run_manager.player.y)
        app.state_manager.change_state(GameState.GAMEPLAY)

    app.run(max_frames=args.max_frames)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
