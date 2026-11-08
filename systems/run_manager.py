"""Run lifecycle manager handling 3-stage biome order, spawning, and stage transitions."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from characters.archer import get_all_character_stats
from combat.combat_system import CombatSystem
from config.balance import (
    BOSS_REWARD_CRYSTALS,
    BOSS_REWARD_GOLD,
    TOTAL_STAGES_PER_RUN,
    TREASURE_CHEST_CRYSTALS,
    TREASURE_CHEST_GOLD,
)
from config.settings import TILE_SIZE
from entities.boss import Boss
from entities.enemy import Enemy
from entities.player import Player
from systems.progression import ProgressionManager
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
    """Orchestrates a 3-stage roguelike run, stage seeds, spawning, and rewards."""

    def __init__(self, progression: ProgressionManager) -> None:
        self.progression: ProgressionManager = progression
        self.run_seed: int = 0
        self.stage_biomes: list[str] = []
        self.current_stage_index: int = 1  # 1..3
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
        """Initialize a fresh 3-stage run with a deterministic seed."""
        if seed is None:
            seed = random.SystemRandom().randint(100_000, 999_999_999)
        self.run_seed = int(seed)
        run_rng = random.Random(self.run_seed)

        self.stage_biomes = self.build_stage_biome_order(run_rng)
        self.current_stage_index = 1
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

        self._load_stage(self.current_stage_index)

    def _load_stage(self, stage_index: int) -> None:
        """Generate dungeon, place player at entrance, and spawn shrines, enemies, and boss."""
        self.current_stage_index = stage_index
        biome_id = self.stage_biomes[stage_index - 1]
        stage_seed = self.run_seed + stage_index * 10_007
        self._stage_rng = random.Random(stage_seed)

        generator = DungeonGenerator(biome_id=biome_id)
        self.dungeon = generator.generate(seed=stage_seed)
        self.combat_system.clear()
        self.portal = None

        assert self.player is not None
        ex, ey = self.dungeon.entrance_room.center
        self.player.x = ex * TILE_SIZE + TILE_SIZE * 0.5
        self.player.y = ey * TILE_SIZE + TILE_SIZE * 0.5

        # Build 3 Shrine entities
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
        self.shrine_system = ShrineSystem(shrines)

        # Spawn enemies and stage boss
        self.enemies = []
        self.boss = None
        for room in self.dungeon.rooms:
            if room.room_type == RoomType.ENTRANCE:
                continue
            if room.room_type == RoomType.BOSS:
                bx, by = room.center
                self.boss = Boss(
                    x=bx * TILE_SIZE + TILE_SIZE * 0.5,
                    y=by * TILE_SIZE + TILE_SIZE * 0.5,
                    room_id=room.room_id,
                    boss_name=self.dungeon.biome.boss_name,
                    stage_index=stage_index,
                )
                self.enemies.append(self.boss)
            else:
                self._spawn_enemies_for_room(room, stage_index)

        self.show_banner(
            f"Stage {stage_index}/{TOTAL_STAGES_PER_RUN}: {self.dungeon.biome.name} (Seed: {stage_seed})"
        )

    def _spawn_enemies_for_room(self, room: Room, stage_index: int) -> None:
        """Populate a room with enemies according to its RoomType."""
        archetypes: list[str] = []
        if room.room_type == RoomType.NORMAL_COMBAT:
            count = self._stage_rng.randint(2, 3 + (1 if stage_index >= 2 else 0))
            pool = ["melee", "fast", "ranged"]
            archetypes = [self._stage_rng.choice(pool) for _ in range(count)]
        elif room.room_type == RoomType.SHRINE:
            archetypes = ["melee", "ranged", "fast"][: 2 + (1 if stage_index == 3 else 0)]
        elif room.room_type == RoomType.ELITE_COMBAT:
            archetypes = ["elite", "melee", "ranged"]
        elif room.room_type == RoomType.MINI_BOSS:
            archetypes = ["mini_boss", "fast"]
        elif room.room_type == RoomType.TREASURE:
            archetypes = ["elite", "fast"]

        x1, y1, x2, y2 = room.inner_bounds
        cx, cy = room.center
        for arch in archetypes:
            for _ in range(12):
                tx = self._stage_rng.randint(max(x1, room.x + 2), min(x2, room.right - 3))
                ty = self._stage_rng.randint(max(y1, room.y + 2), min(y2, room.bottom - 3))
                # Avoid spawning directly on top of a Shrine at room center
                if room.room_type == RoomType.SHRINE and abs(tx - cx) <= 1 and abs(ty - cy) <= 1:
                    continue
                wx = tx * TILE_SIZE + TILE_SIZE * 0.5
                wy = ty * TILE_SIZE + TILE_SIZE * 0.5
                self.enemies.append(Enemy(x=wx, y=wy, archetype=arch, room_id=room.room_id))
                break

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
        """Grant boss rewards and spawn the stage exit portal in the boss room."""
        if self.dungeon is None or self.portal is not None:
            return
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

    def advance_stage_or_finish(self) -> str:
        """Transition to the next stage or return 'treasure_room' if Stage 3 is complete."""
        if self.current_stage_index < TOTAL_STAGES_PER_RUN:
            assert self.player is not None
            self.player.heal(int(self.player.max_hp * 0.35))
            self._load_stage(self.current_stage_index + 1)
            return "gameplay"

        self.progression.data.runs_completed += 1
        self.progression.persist()
        return "treasure_room"

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
