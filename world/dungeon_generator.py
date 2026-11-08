"""Deterministic procedural dungeon generator for THE FRACTURED GATE."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from config.balance import REQUIRED_SHRINES_PER_STAGE
from world.biome import BiomeConfig, get_biome_config
from world.corridor import Corridor
from world.dungeon_graph import DungeonGraph
from world.room import Room, RoomType
from world.tilemap import TileMap, TileType


@dataclass
class GeneratedDungeon:
    """Complete output of the procedural dungeon generator for a single stage."""

    seed: int
    biome: BiomeConfig
    rooms: list[Room]
    corridors: list[Corridor]
    graph: DungeonGraph
    tilemap: TileMap
    entrance_room: Room
    boss_room: Room
    shrine_rooms: list[Room]
    shrine_positions: list[tuple[int, int]] = field(default_factory=list)

    def get_room_by_id(self, room_id: int) -> Room:
        """Retrieve a room by its integer ID."""
        for room in self.rooms:
            if room.room_id == room_id:
                return room
        raise KeyError(f"Room ID {room_id} not found.")

    def get_room_at_tile(self, tx: int, ty: int) -> Room | None:
        """Return the room containing tile (tx, ty), or None if in corridor/void."""
        for room in self.rooms:
            if room.contains_tile(tx, ty):
                return room
        return None


class DungeonGenerator:
    """Generates non-overlapping rooms, graph connectivity, corridors, and tilemaps."""

    def __init__(self, biome_id: str = "enchanted_forest") -> None:
        self.biome: BiomeConfig = get_biome_config(biome_id)

    def generate(self, seed: int) -> GeneratedDungeon:
        """Generate a valid, connected procedural dungeon deterministically from seed."""
        rng = random.Random(seed)
        target_rooms = rng.randint(self.biome.min_rooms, self.biome.max_rooms)
        target_rooms = max(target_rooms, 2 + REQUIRED_SHRINES_PER_STAGE + 2)

        rooms = self._place_rooms(rng, target_rooms)
        graph = DungeonGraph(rooms)

        # Preliminary MST to determine Entrance and Boss rooms by topological distance
        preliminary_graph = DungeonGraph(rooms)
        preliminary_graph.build_mst_and_loops(rng, extra_loop_chance=0.0)

        entrance_room = self._select_entrance_room(rooms)
        prelim_distances = preliminary_graph.bfs_distances(entrance_room.room_id)
        boss_room = self._select_boss_room(rooms, entrance_room, prelim_distances)

        # Reset room connections and rebuild graph keeping boss room as a leaf or gated node
        for r in rooms:
            r.connected_room_ids.clear()
        graph = DungeonGraph(rooms)
        graph.build_mst_and_loops(
            rng,
            extra_loop_chance=self.biome.extra_loop_chance,
            boss_room_id=boss_room.room_id,
        )

        # Assign room types (Entrance, Boss, 3 Shrines, Elite, Mini-Boss, Treasure, Normal)
        shrine_rooms = self._assign_room_types(rng, rooms, graph, entrance_room, boss_room)

        # Carve rooms and corridors onto TileMap
        corridors = self._build_corridors(rng, graph)
        tilemap = TileMap(self.biome.grid_width, self.biome.grid_height, self.biome)
        self._carve_dungeon_tiles(tilemap, rooms, corridors, boss_room)

        # Ensure 100% tile-level walkability from entrance center to all room centers
        self._ensure_tile_connectivity(tilemap, rooms, corridors, entrance_room)

        # Place boss gate tiles on corridor entrances bordering the boss room
        self._place_boss_gates(tilemap, boss_room)

        # Build surrounding walls around all carved floors/corridors
        tilemap.build_walls_around_floors()

        shrine_positions = [sr.center for sr in shrine_rooms]

        return GeneratedDungeon(
            seed=seed,
            biome=self.biome,
            rooms=rooms,
            corridors=corridors,
            graph=graph,
            tilemap=tilemap,
            entrance_room=entrance_room,
            boss_room=boss_room,
            shrine_rooms=shrine_rooms,
            shrine_positions=shrine_positions,
        )

    def _place_rooms(self, rng: random.Random, target_count: int) -> list[Room]:
        """Place non-overlapping rooms within the biome grid with fallback relaxation."""
        rooms: list[Room] = []
        margin = 4
        padding = self.biome.room_padding

        max_attempts = 1200
        attempts = 0
        while len(rooms) < target_count and attempts < max_attempts:
            attempts += 1
            # Gradually relax padding if grid is tight after many attempts
            current_padding = padding if attempts < 600 else max(2, padding - 1)
            min_size = self.biome.min_room_size
            max_size = self.biome.max_room_size if attempts < 800 else min_size + 2

            w = rng.randint(min_size, max_size)
            h = rng.randint(min_size, max_size)
            max_x = self.biome.grid_width - w - margin
            max_y = self.biome.grid_height - h - margin
            if max_x <= margin or max_y <= margin:
                break

            x = rng.randint(margin, max_x)
            y = rng.randint(margin, max_y)
            candidate = Room(room_id=len(rooms), x=x, y=y, width=w, height=h)

            if all(not candidate.intersects(existing, padding=current_padding) for existing in rooms):
                rooms.append(candidate)

        # Deterministic grid-slot fallback if random sampling placed fewer than minimum rooms
        if len(rooms) < target_count:
            slot_size = self.biome.min_room_size + 4
            for gy in range(margin, self.biome.grid_height - slot_size - margin, slot_size):
                for gx in range(margin, self.biome.grid_width - slot_size - margin, slot_size):
                    if len(rooms) >= target_count:
                        break
                    candidate = Room(
                        room_id=len(rooms),
                        x=gx,
                        y=gy,
                        width=self.biome.min_room_size,
                        height=self.biome.min_room_size,
                    )
                    if all(not candidate.intersects(existing, padding=2) for existing in rooms):
                        rooms.append(candidate)

        return rooms

    def _select_entrance_room(self, rooms: list[Room]) -> Room:
        """Pick the room closest to the top-left quadrant as the entrance room."""
        return min(rooms, key=lambda r: math.hypot(r.center[0], r.center[1]))

    def _select_boss_room(
        self,
        rooms: list[Room],
        entrance_room: Room,
        distances: dict[int, int],
    ) -> Room:
        """Select the room furthest from entrance in graph hops and Euclidean distance."""
        candidates = [r for r in rooms if r.room_id != entrance_room.room_id]
        return max(
            candidates,
            key=lambda r: (
                distances.get(r.room_id, 0),
                DungeonGraph.room_distance(entrance_room, r),
            ),
        )

    def _assign_room_types(
        self,
        rng: random.Random,
        rooms: list[Room],
        graph: DungeonGraph,
        entrance_room: Room,
        boss_room: Room,
    ) -> list[Room]:
        """Assign Entrance, Boss, 3 Shrines, and combat/special rooms."""
        entrance_room.room_type = RoomType.ENTRANCE
        entrance_room.cleared = True
        entrance_room.visited = True

        boss_room.room_type = RoomType.BOSS

        remaining = [
            r
            for r in rooms
            if r.room_id not in (entrance_room.room_id, boss_room.room_id)
        ]
        rng.shuffle(remaining)

        # Sort remaining by distance from entrance so shrines are well distributed
        distances = graph.bfs_distances(entrance_room.room_id)
        remaining.sort(key=lambda r: distances.get(r.room_id, 1), reverse=True)

        shrine_rooms: list[Room] = []
        if len(remaining) >= REQUIRED_SHRINES_PER_STAGE:
            # Spread 3 shrines across distant, mid, and near bands
            step = max(1, len(remaining) // REQUIRED_SHRINES_PER_STAGE)
            chosen_indices: list[int] = []
            for i in range(REQUIRED_SHRINES_PER_STAGE):
                idx = min(len(remaining) - 1, i * step)
                while idx in chosen_indices and idx + 1 < len(remaining):
                    idx += 1
                chosen_indices.append(idx)
            while len(chosen_indices) < REQUIRED_SHRINES_PER_STAGE:
                for idx in range(len(remaining)):
                    if idx not in chosen_indices:
                        chosen_indices.append(idx)
                        break

            for idx in chosen_indices[:REQUIRED_SHRINES_PER_STAGE]:
                room = remaining[idx]
                room.room_type = RoomType.SHRINE
                shrine_rooms.append(room)

        other_rooms = [
            r
            for r in remaining
            if r.room_type != RoomType.SHRINE
        ]
        rng.shuffle(other_rooms)

        special_cycle = [
            RoomType.ELITE_COMBAT,
            RoomType.MINI_BOSS,
            RoomType.TREASURE,
        ]
        for idx, room in enumerate(other_rooms):
            if idx < len(special_cycle) and len(other_rooms) >= 4:
                room.room_type = special_cycle[idx]
            else:
                room.room_type = RoomType.NORMAL_COMBAT

        return shrine_rooms

    def _build_corridors(
        self,
        rng: random.Random,
        graph: DungeonGraph,
    ) -> list[Corridor]:
        """Create Corridor objects for every edge in the DungeonGraph."""
        corridors: list[Corridor] = []
        for idx, (room_a_id, room_b_id) in enumerate(graph.edges):
            room_a = graph.rooms_by_id[room_a_id]
            room_b = graph.rooms_by_id[room_b_id]
            corridor = Corridor(
                corridor_id=idx,
                room_a_id=room_a_id,
                room_b_id=room_b_id,
                start_tile=room_a.center,
                end_tile=room_b.center,
                width=self.biome.corridor_width,
                horizontal_first=rng.choice([True, False]),
            )
            corridors.append(corridor)
        return corridors

    def _carve_dungeon_tiles(
        self,
        tilemap: TileMap,
        rooms: list[Room],
        corridors: list[Corridor],
        boss_room: Room,
    ) -> None:
        """Carve corridor tiles first, then room floor tiles so room interiors stay clean."""
        for corridor in corridors:
            for tx, ty in corridor.tiles:
                if 1 <= tx < tilemap.width - 1 and 1 <= ty < tilemap.height - 1:
                    tilemap.set_tile(tx, ty, TileType.CORRIDOR)

        for room in rooms:
            for ty in range(room.y, room.bottom):
                for tx in range(room.x, room.right):
                    tilemap.set_tile(tx, ty, TileType.FLOOR)

    def _ensure_tile_connectivity(
        self,
        tilemap: TileMap,
        rooms: list[Room],
        corridors: list[Corridor],
        entrance_room: Room,
    ) -> None:
        """Verify tile walkability to every room center and carve direct bridges if needed."""
        reachable = tilemap.reachable_tiles_from(entrance_room.center, ignore_boss_lock=True)
        for room in rooms:
            if room.center not in reachable:
                bridge = Corridor(
                    corridor_id=len(corridors),
                    room_a_id=entrance_room.room_id,
                    room_b_id=room.room_id,
                    start_tile=entrance_room.center,
                    end_tile=room.center,
                    width=self.biome.corridor_width,
                    horizontal_first=True,
                )
                corridors.append(bridge)
                for tx, ty in bridge.tiles:
                    if 1 <= tx < tilemap.width - 1 and 1 <= ty < tilemap.height - 1:
                        if tilemap.get_tile(tx, ty) == TileType.VOID:
                            tilemap.set_tile(tx, ty, TileType.CORRIDOR)
                reachable = tilemap.reachable_tiles_from(
                    entrance_room.center, ignore_boss_lock=True
                )

    def _place_boss_gates(self, tilemap: TileMap, boss_room: Room) -> None:
        """Place locked boss gate tiles along corridor tiles immediately outside boss_room."""
        gate_coords: list[tuple[int, int]] = []
        # Check the 1-tile perimeter around boss_room for CORRIDOR tiles
        for tx in range(boss_room.x - 1, boss_room.right + 1):
            for ty in (boss_room.y - 1, boss_room.bottom):
                if tilemap.get_tile(tx, ty) == TileType.CORRIDOR:
                    gate_coords.append((tx, ty))
        for ty in range(boss_room.y, boss_room.bottom):
            for tx in (boss_room.x - 1, boss_room.right):
                if tilemap.get_tile(tx, ty) == TileType.CORRIDOR:
                    gate_coords.append((tx, ty))

        for tx, ty in gate_coords:
            tilemap.set_tile(tx, ty, TileType.BOSS_GATE_LOCKED)
            tilemap.boss_gate_tiles.append((tx, ty))
