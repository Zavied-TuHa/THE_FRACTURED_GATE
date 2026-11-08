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
    """Simulate a 3-stage run: activate 3 shrines, unlock boss gate, progress to Treasure Room."""
    save_sys = SaveSystem(
        save_path=tmp_path / "profile.save.json",
        backup_path=tmp_path / "profile.save.bak",
    )
    prog = ProgressionManager(save_sys)
    run_mgr = RunManager(prog)
    run_mgr.start_new_run(character_id="warrior", seed=98765)

    for stage_idx in (1, 2, 3):
        assert run_mgr.current_stage_index == stage_idx
        assert run_mgr.dungeon is not None
        assert run_mgr.shrine_system is not None
        assert run_mgr.player is not None

        # Clear all non-boss enemies so shrines are unguarded
        for enemy in run_mgr.enemies:
            if enemy is not run_mgr.boss:
                enemy.alive = False

        # Activate all 3 shrines
        for shrine in run_mgr.shrine_system.shrines:
            wx, wy = shrine.world_pos
            run_mgr.player.x = wx
            run_mgr.player.y = wy
            ok, _, gold, crys = run_mgr.shrine_system.try_activate_nearby_shrine(
                run_mgr.player.x,
                run_mgr.player.y,
                run_mgr.enemies,
                run_mgr.dungeon.tilemap,
            )
            assert ok is True
            run_mgr.award_currency(gold=gold, crystals=crys)

        assert run_mgr.shrine_system.all_activated is True
        for gx, gy in run_mgr.dungeon.tilemap.boss_gate_tiles:
            assert run_mgr.dungeon.tilemap.get_tile(gx, gy) == TileType.BOSS_GATE_UNLOCKED

        # Defeat boss and use stage portal
        assert run_mgr.boss is not None
        run_mgr.boss.alive = False
        run_mgr.handle_boss_defeated()
        assert run_mgr.portal is not None

        next_screen = run_mgr.advance_stage_or_finish()
        if stage_idx < 3:
            assert next_screen == "gameplay"
        else:
            assert next_screen == "treasure_room"

    # Claim final Treasure Chest
    gold_chest, crys_chest = run_mgr.claim_treasure_chest()
    assert gold_chest > 0 and crys_chest > 0
    assert run_mgr.treasure_collected is True
    assert prog.data.runs_completed == 1
