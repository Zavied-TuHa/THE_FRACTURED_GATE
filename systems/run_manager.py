"""Run lifecycle manager handling 3-stage, 5-substage progression, spawning, and transitions."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from characters.archer import get_all_character_stats
from combat.combat_system import CombatSystem
from config.balance import (
    BOSS_REWARD_CRYSTALS,
    BOSS_REWARD_GOLD,
    REQUIRED_SHRINES_PER_STAGE_V2,
    SHRINES_PER_SUBSTAGE,
    SUBSTAGES_PER_STAGE,
    TOTAL_STAGES_PER_RUN,
    TREASURE_CHEST_CRYSTALS,
    TREASURE_CHEST_GOLD,
)
from config.settings import TILE_SIZE
from entities.boss import Boss
from entities.enemy import Enemy
from entities.player import Player
from systems.progression import ProgressionManager
from systems.rng_streams import SeedHierarchy
from systems.shrine_system import Shrine, ShrineSystem
from world.dungeon_generator import DungeonGenerator, GeneratedDungeon
from world.room import Room, RoomType


@dataclass
class StagePortal:
    """Interactive portal spawned after defeating the stage boss."""

    tile_x: int
    tile_y: int
    radius: float = 24.0

    @property
    def world_pos(self) -> tuple[float, float]:
        """Return world pixel coordinates of the portal."""
        return (
            self.tile_x * TILE_SIZE + TILE_SIZE * 0.5,
            self.tile_y * TILE_SIZE + TILE_SIZE * 0.5,
        )

    def is_player_in_range(self, px: float, py: float) -> bool:
        """Return True if player is close enough to enter the portal."""
        wx, wy = self.world_pos
        return math.hypot(px - wx, py - wy) <= self.radius


class RunManager:
    """Orchestrates a 3-stage × 5-substage roguelike run, seeds, spawning, and transitions."""

    def __init__(self, progression: ProgressionManager) -> None:
        self.progression: ProgressionManager = progression
        self.run_seed: int = 0
        self.seed_hierarchy: SeedHierarchy = SeedHierarchy(0)
        self.stage_biomes: list[str] = []
        self.current_stage_index: int = 1  # 1..3
        self.current_substage_index: int = 1  # 1..5
        self.stage_shrines_activated: int = 0  # 0..5 within current stage
        self.total_shrines_activated: int = 0  # 0..15 across the entire run
        self.in_boss_room: bool = False
        self.stage_boss_defeated: bool = False
        self.boss_arena_initialized_for_stage: int = 0
        self.is_run_active: bool = False
        self.run_outcome: str = "idle"
        self.selected_character_id: str = "warrior"

        self.dungeon: GeneratedDungeon | None = None
        self.player: Player | None = None
        self.enemies: list[Enemy] = []
        self.boss: Boss | None = None
        self.shrine_system: ShrineSystem | None = None
        self.combat_system: CombatSystem = CombatSystem()
        self.portal: StagePortal | None = None

        self.run_gold_earned: int = 0
        self.run_crystals_earned: int = 0
        self.enemies_slain: int = 0
        self.treasure_collected: bool = False
        self.status_banner_text: str = ""
        self.status_banner_timer: float = 0.0
        self._stage_rng: random.Random = random.Random(0)

    @staticmethod
    def build_stage_biome_order(rng: random.Random) -> list[str]:
        """Randomize Stage 1 & 2 between Enchanted Forest and Crystal Cavern; Stage 3 is Demon Castle."""
        first_two = ["enchanted_forest", "crystal_cavern"]
        rng.shuffle(first_two)
        return [first_two[0], first_two[1], "demon_castle"]

    def start_new_run(
        self,
        character_id: str = "warrior",
        seed: int | None = None,
    ) -> None:
        """Initialize a fresh 3-stage × 5-substage run with a deterministic seed."""
        if seed is None:
            seed = random.SystemRandom().randint(100_000, 999_999_999)
        self.run_seed = int(seed)
        self.seed_hierarchy = SeedHierarchy(self.run_seed)
        run_rng = self.seed_hierarchy.run_rng()

        self.stage_biomes = self.build_stage_biome_order(run_rng)
        self.current_stage_index = 1
        self.current_substage_index = 1
        self.stage_shrines_activated = 0
        self.total_shrines_activated = 0
        self.in_boss_room = False
        self.stage_boss_defeated = False
        self.boss_arena_initialized_for_stage = 0
        self.is_run_active = True
        self.run_outcome = "in_progress"
        self.selected_character_id = character_id
        self.run_gold_earned = 0
        self.run_crystals_earned = 0
        self.enemies_slain = 0
        self.treasure_collected = False

        all_stats = get_all_character_stats()
        char_stats = all_stats.get(character_id, all_stats["warrior"])
        s1_unlocked = self.progression.is_skill_unlocked(character_id, "skill_1")
        s2_unlocked = self.progression.is_skill_unlocked(character_id, "skill_2")

        self.player = Player(
            x=0.0,
            y=0.0,
            stats=char_stats,
            skill_1_unlocked=s1_unlocked,
            skill_2_unlocked=s2_unlocked,
        )
        self.progression.data.runs_started += 1
        self.progression.persist()

        self._load_substage(self.current_stage_index, self.current_substage_index)

    def sync_player_room_ownership(self) -> int | None:
        """Update player.current_room_id and player.current_room_bounds from current tile position."""
        if self.player is None or self.dungeon is None:
            return None
        current_room = self.dungeon.get_room_at_tile(*self.player.tile_pos)
        if current_room is not None:
            self.player.current_room_id = current_room.room_id
            self.player.current_room_bounds = (
                float((current_room.x + 1) * TILE_SIZE),
                float((current_room.y + 1) * TILE_SIZE),
                float((current_room.right - 1) * TILE_SIZE),
                float((current_room.bottom - 1) * TILE_SIZE),
            )
        else:
            self.player.current_room_id = None
            self.player.current_room_bounds = None
        return self.player.current_room_id

    def _load_substage(self, stage_index: int, substage_index: int) -> None:
        """Generate a substage dungeon, place player at entrance, and spawn its shrine and enemies."""
        self.current_stage_index = stage_index
        self.current_substage_index = substage_index
        self.in_boss_room = False
        self.stage_boss_defeated = False

        biome_id = self.stage_biomes[stage_index - 1]
        self._stage_rng = self.seed_hierarchy.substage_rng(stage_index, substage_index)

        generator = DungeonGenerator(biome_id=biome_id)
        self.dungeon = generator.generate_substage(
            run_seed=self.run_seed,
            stage_index=stage_index,
            substage_index=substage_index,
        )
        self.combat_system.clear()
        self.portal = None
        self.boss = None

        assert self.player is not None
        ex, ey = self.dungeon.entrance_room.center
        self.player.x = ex * TILE_SIZE + TILE_SIZE * 0.5
        self.player.y = ey * TILE_SIZE + TILE_SIZE * 0.5
        self.sync_player_room_ownership()

        # Build the single mandatory Shrine entity for this substage
        shrines: list[Shrine] = []
        for idx, s_room in enumerate(self.dungeon.shrine_rooms):
            cx, cy = s_room.center
            shrines.append(
                Shrine(
                    shrine_id=idx + 1,
                    room_id=s_room.room_id,
                    tile_x=cx,
                    tile_y=cy,
                )
            )
        self.shrine_system = ShrineSystem(
            shrines, required_count=SHRINES_PER_SUBSTAGE
        )

        # Spawn enemies per room using isolated room RNG streams
        self.enemies = []
        for room in self.dungeon.rooms:
            if room.room_type == RoomType.ENTRANCE:
                continue
            self._spawn_enemies_for_room(room, stage_index, substage_index)

        self.show_banner(
            f"Stage {stage_index}-{substage_index}: {self.dungeon.biome.name} "
            f"(Shrines: {self.stage_shrines_activated}/{REQUIRED_SHRINES_PER_STAGE_V2})"
        )

    def can_enter_boss_room(self) -> bool:
        """Return True only when all 5 mandatory shrines of the current stage are activated."""
        return (
            self.stage_shrines_activated >= REQUIRED_SHRINES_PER_STAGE_V2
            and self.current_substage_index == SUBSTAGES_PER_STAGE
        )

    def _load_boss_arena(self, stage_index: int) -> None:
        """Generate the dedicated Boss Arena after Shrine 5 of the stage is activated."""
        if not self.can_enter_boss_room():
            raise RuntimeError(
                f"Cannot enter Stage {stage_index} Boss Room before activating all "
                f"{REQUIRED_SHRINES_PER_STAGE_V2} Stage Shrines "
                f"(current: {self.stage_shrines_activated})."
            )
        if self.in_boss_room and self.boss_arena_initialized_for_stage == stage_index:
            return

        self.current_stage_index = stage_index
        self.in_boss_room = True
        self.stage_boss_defeated = False
        self.boss_arena_initialized_for_stage = stage_index
        biome_id = self.stage_biomes[stage_index - 1]
        self._stage_rng = self.seed_hierarchy.stage_rng(stage_index)

        generator = DungeonGenerator(biome_id=biome_id)
        self.dungeon = generator.generate_boss_arena(
            run_seed=self.run_seed,
            stage_index=stage_index,
        )
        self.combat_system.clear()
        self.portal = None
        self.shrine_system = ShrineSystem([], required_count=0)

        assert self.player is not None
        ex, ey = self.dungeon.entrance_room.center
        self.player.x = ex * TILE_SIZE + TILE_SIZE * 0.5
        self.player.y = ey * TILE_SIZE + TILE_SIZE * 0.5
        self.sync_player_room_ownership()

        boss_room = self.dungeon.boss_room
        bx, by = boss_room.center
        room_bounds = (
            float((boss_room.x + 1) * TILE_SIZE),
            float((boss_room.y + 1) * TILE_SIZE),
            float((boss_room.right - 1) * TILE_SIZE),
            float((boss_room.bottom - 1) * TILE_SIZE),
        )
        self.boss = Boss(
            x=bx * TILE_SIZE + TILE_SIZE * 0.5,
            y=by * TILE_SIZE + TILE_SIZE * 0.5,
            room_id=boss_room.room_id,
            boss_name=self.dungeon.biome.boss_name,
            stage_index=stage_index,
            room_bounds=room_bounds,
        )
        self.enemies = [self.boss]

        self.show_banner(
            f"Stage {stage_index} BOSS: {self.dungeon.biome.boss_name}!"
        )

    def _spawn_enemies_for_room(
        self,
        room: Room,
        stage_index: int,
        substage_index: int = 1,
    ) -> None:
        """Populate a room with enemies according to its RoomType and isolated RNG stream."""
        room_rng = self.seed_hierarchy.enemy_wave_rng(
            stage_index, substage_index, room.room_id
        )
        archetypes: list[str] = []
        if room.room_type in (RoomType.ENEMY, RoomType.NORMAL_COMBAT):
            base_max = 3 + (1 if stage_index >= 2 else 0) + (1 if substage_index >= 4 else 0)
            count = room_rng.randint(2, base_max)
            pool = ["melee", "fast", "ranged"]
            archetypes = [room_rng.choice(pool) for _ in range(count)]
        elif room.room_type == RoomType.SHRINE:
            archetypes = ["melee", "ranged", "fast"][: 2 + (1 if stage_index == 3 else 0)]
        elif room.room_type == RoomType.ELITE_COMBAT:
            archetypes = ["elite", "melee", "ranged"]
        elif room.room_type == RoomType.MINI_BOSS:
            archetypes = ["mini_boss", "fast"]
        elif room.room_type in (RoomType.TREASURE, RoomType.CHEST):
            archetypes = ["elite", "fast"]
        elif room.room_type in (RoomType.SPECIAL, RoomType.SHOP):
            # Safe / non-combat utility rooms in substages have no default enemies
            return

        x1, y1, x2, y2 = room.inner_bounds
        cx, cy = room.center
        room_bounds = (
            float((room.x + 1) * TILE_SIZE),
            float((room.y + 1) * TILE_SIZE),
            float((room.right - 1) * TILE_SIZE),
            float((room.bottom - 1) * TILE_SIZE),
        )
        for arch in archetypes:
            for _ in range(12):
                tx = room_rng.randint(max(x1, room.x + 2), min(x2, room.right - 3))
                ty = room_rng.randint(max(y1, room.y + 2), min(y2, room.bottom - 3))
                # Avoid spawning directly on top of a Shrine at room center
                if room.room_type == RoomType.SHRINE and abs(tx - cx) <= 1 and abs(ty - cy) <= 1:
                    continue
                wx = tx * TILE_SIZE + TILE_SIZE * 0.5
                wy = ty * TILE_SIZE + TILE_SIZE * 0.5
                self.enemies.append(
                    Enemy(
                        x=wx,
                        y=wy,
                        archetype=arch,
                        room_id=room.room_id,
                        room_bounds=room_bounds,
                    )
                )
                break

    def try_activate_shrine(self) -> tuple[bool, str]:
        """Attempt to activate a nearby Shrine and execute immediate Substage / Boss transition."""
        if (
            self.player is None
            or self.dungeon is None
            or self.shrine_system is None
            or self.in_boss_room
        ):
            return (False, "")

        activated, msg, gold, crystals = self.shrine_system.try_activate_nearby_shrine(
            self.player.x,
            self.player.y,
            self.enemies,
            self.dungeon.tilemap,
        )
        if not activated:
            if msg:
                self.show_banner(msg)
            return (False, msg)

        self.award_currency(gold=gold, crystals=crystals)
        self.stage_shrines_activated += 1
        self.total_shrines_activated += 1

        if self.current_substage_index < SUBSTAGES_PER_STAGE:
            next_sub = self.current_substage_index + 1
            self._load_substage(self.current_stage_index, next_sub)
            transition_msg = (
                f"Shrine {self.stage_shrines_activated}/{REQUIRED_SHRINES_PER_STAGE_V2} Activated! "
                f"Advancing to Stage {self.current_stage_index}-{next_sub}!"
            )
            self.show_banner(transition_msg)
            return (True, transition_msg)

        # Shrine 5 of the current stage activated -> transition immediately to Stage Boss Arena
        self._load_boss_arena(self.current_stage_index)
        transition_msg = (
            f"All {REQUIRED_SHRINES_PER_STAGE_V2} Stage Shrines Activated! "
            f"Entering {self.dungeon.biome.boss_name}'s Lair!"
        )
        self.show_banner(transition_msg)
        return (True, transition_msg)

    def show_banner(self, text: str, duration: float = 3.2) -> None:
        """Display a status message banner on the HUD."""
        self.status_banner_text = text
        self.status_banner_timer = duration

    def award_currency(self, gold: int = 0, crystals: int = 0) -> None:
        """Award currency both to current run tally and persistent progression."""
        self.run_gold_earned += gold
        self.run_crystals_earned += crystals
        self.progression.grant_rewards(gold=gold, blue_crystals=crystals)

    def handle_boss_defeated(self) -> None:
        """Grant boss rewards once and spawn the stage exit portal in the boss room."""
        if (
            self.dungeon is None
            or not self.in_boss_room
            or self.stage_boss_defeated
            or self.portal is not None
        ):
            return
        self.stage_boss_defeated = True
        self.award_currency(gold=BOSS_REWARD_GOLD, crystals=BOSS_REWARD_CRYSTALS)
        bx, by = self.dungeon.boss_room.center
        self.portal = StagePortal(tile_x=bx, tile_y=by)
        if self.current_stage_index < TOTAL_STAGES_PER_RUN:
            self.show_banner(
                "Stage Boss Vanquished! Press [F] at the Portal to enter the next Stage."
            )
        else:
            self.show_banner(
                "Final Boss Vanquished! Press [F] at the Portal to enter the Treasure Room!"
            )

    def try_use_stage_portal(self) -> tuple[bool, str]:
        """Interact with the StagePortal ([F]) after defeating the Stage Boss."""
        if (
            self.player is None
            or self.portal is None
            or not self.stage_boss_defeated
        ):
            return (False, "")
        if not self.portal.is_player_in_range(self.player.x, self.player.y):
            return (False, "")
        self.portal = None
        next_state = self.advance_stage_or_finish()
        return (True, next_state)

    def advance_stage_or_finish(self) -> str:
        """Transition to the next stage's Substage 1 or return 'treasure_room' after Stage 3."""
        if self.current_stage_index < TOTAL_STAGES_PER_RUN:
            assert self.player is not None
            self.player.heal(int(self.player.max_hp * 0.35))
            self.stage_shrines_activated = 0
            self.in_boss_room = False
            self.stage_boss_defeated = False
            self._load_substage(self.current_stage_index + 1, 1)
            return "gameplay"

        self.is_run_active = False
        self.run_outcome = "victory"
        self.combat_system.clear()
        self.progression.data.runs_completed += 1
        self.progression.persist()
        return "treasure_room"

    def handle_player_death(self) -> None:
        """Mark the active run as ended due to Game Over (player death)."""
        self.is_run_active = False
        self.run_outcome = "game_over"
        self.combat_system.clear()

    def abort_run(self) -> None:
        """Cleanly abort the active run via Pause Quit without corrupting persistent progression."""
        self.is_run_active = False
        self.run_outcome = "aborted"
        self.combat_system.clear()
        self.portal = None

    def claim_treasure_chest(self) -> tuple[int, int]:
        """Open the final Treasure Room chest and award large Gold and Blue Crystal payout."""
        if self.treasure_collected:
            return (0, 0)
        self.treasure_collected = True
        self.award_currency(
            gold=TREASURE_CHEST_GOLD,
            crystals=TREASURE_CHEST_CRYSTALS,
        )
        return (TREASURE_CHEST_GOLD, TREASURE_CHEST_CRYSTALS)
