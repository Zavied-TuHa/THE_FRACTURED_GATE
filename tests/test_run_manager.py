"""Automated tests for RunManager, stage biome order, ShrineSystem, and full run flow."""

from __future__ import annotations

from pathlib import Path
import random

from config.settings import TILE_SIZE
from systems.progression import ProgressionManager
from systems.run_manager import RunManager
from systems.save_system import SaveSystem
from world.tilemap import TileType


def test_stage_biome_order_randomization() -> None:
    """Verify Stage 1 & 2 randomize Enchanted Forest / Crystal Cavern and Stage 3 is Demon Castle."""
    seen_first_stages: set[str] = set()
    for seed in range(1, 30):
        order = RunManager.build_stage_biome_order(random.Random(seed))
        assert len(order) == 3
        assert set(order[:2]) == {"enchanted_forest", "crystal_cavern"}
        assert order[2] == "demon_castle"
        seen_first_stages.add(order[0])

    assert seen_first_stages == {"enchanted_forest", "crystal_cavern"}


def test_full_run_shrines_boss_and_treasure_flow(tmp_path: Path) -> None:
    """Simulate a full Revision 2.0 3-stage × 5-substage (15 shrines) run to Treasure Room."""
    save_sys = SaveSystem(
        save_path=tmp_path / "profile.save.json",
        backup_path=tmp_path / "profile.save.bak",
    )
    prog = ProgressionManager(save_sys)
    run_mgr = RunManager(prog)
    run_mgr.start_new_run(character_id="warrior", seed=98765)

    for stage_idx in (1, 2, 3):
        assert run_mgr.current_stage_index == stage_idx
        assert run_mgr.stage_shrines_activated == 0
        assert run_mgr.in_boss_room is False

        for substage_idx in (1, 2, 3, 4, 5):
            assert run_mgr.current_substage_index == substage_idx
            assert run_mgr.dungeon is not None
            assert run_mgr.shrine_system is not None
            assert run_mgr.player is not None
            assert len(run_mgr.shrine_system.shrines) == 1

            # Clear all enemies in the substage so the shrine is unguarded
            for enemy in run_mgr.enemies:
                enemy.alive = False

            shrine = run_mgr.shrine_system.shrines[0]
            wx, wy = shrine.world_pos
            run_mgr.player.x = wx
            run_mgr.player.y = wy
            ok, _ = run_mgr.try_activate_shrine()
            assert ok is True
            assert run_mgr.stage_shrines_activated == substage_idx

            if substage_idx < 5:
                assert run_mgr.in_boss_room is False
                assert run_mgr.current_substage_index == substage_idx + 1
            else:
                assert run_mgr.in_boss_room is True

        # Now in Stage Boss Arena
        assert run_mgr.boss is not None
        assert run_mgr.dungeon is not None
        for gx, gy in run_mgr.dungeon.tilemap.boss_gate_tiles:
            assert run_mgr.dungeon.tilemap.get_tile(gx, gy) == TileType.BOSS_GATE_UNLOCKED

        # Defeat boss and use stage portal
        run_mgr.boss.alive = False
        run_mgr.handle_boss_defeated()
        assert run_mgr.portal is not None

        next_screen = run_mgr.advance_stage_or_finish()
        if stage_idx < 3:
            assert next_screen == "gameplay"
        else:
            assert next_screen == "treasure_room"

    assert run_mgr.total_shrines_activated == 15
    # Claim final Treasure Chest
    gold_chest, crys_chest = run_mgr.claim_treasure_chest()
    assert gold_chest > 0 and crys_chest > 0
    assert run_mgr.treasure_collected is True
    assert prog.data.runs_completed == 1
