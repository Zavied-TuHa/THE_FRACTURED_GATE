"""Graph-based room connectivity, Minimum Spanning Tree (MST), and BFS reachability."""

from __future__ import annotations

from collections import deque
import math
import random
from typing import Iterable

from world.room import Room


class DungeonGraph:
    """Undirected graph representing room connectivity in a generated dungeon."""

    def __init__(self, rooms: Iterable[Room]) -> None:
        self.rooms_by_id: dict[int, Room] = {r.room_id: r for r in rooms}
        self.adjacency: dict[int, set[int]] = {
            r.room_id: set() for r in self.rooms_by_id.values()
        }
        self.edges: list[tuple[int, int]] = []

    def add_edge(self, room_a_id: int, room_b_id: int) -> bool:
        """Add an undirected edge between two rooms if not already present."""
        if room_a_id == room_b_id:
            return False
        if room_b_id in self.adjacency[room_a_id]:
            return False

        self.adjacency[room_a_id].add(room_b_id)
        self.adjacency[room_b_id].add(room_a_id)
        edge = (min(room_a_id, room_b_id), max(room_a_id, room_b_id))
        self.edges.append(edge)

        room_a = self.rooms_by_id[room_a_id]
        room_b = self.rooms_by_id[room_b_id]
        if room_b_id not in room_a.connected_room_ids:
            room_a.connected_room_ids.append(room_b_id)
        if room_a_id not in room_b.connected_room_ids:
            room_b.connected_room_ids.append(room_a_id)
        return True

    @staticmethod
    def room_distance(room_a: Room, room_b: Room) -> float:
        """Return Euclidean distance between two room centers."""
        ax, ay = room_a.center
        bx, by = room_b.center
        return math.hypot(bx - ax, by - ay)

    def build_mst_and_loops(
        self,
        rng: random.Random,
        extra_loop_chance: float = 0.25,
        boss_room_id: int | None = None,
    ) -> list[tuple[int, int]]:
        """Build a Minimum Spanning Tree using Prim's algorithm, then add optional maze loops."""
        room_ids = sorted(self.rooms_by_id.keys())
        if len(room_ids) <= 1:
            return []

        visited: set[int] = {room_ids[0]}
        unvisited: set[int] = set(room_ids[1:])

        while unvisited:
            best_pair: tuple[int, int] | None = None
            best_dist = float("inf")

            for u in sorted(visited):
                for v in sorted(unvisited):
                    dist = self.room_distance(self.rooms_by_id[u], self.rooms_by_id[v])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (u, v)

            if best_pair is None:
                break

            u, v = best_pair
            self.add_edge(u, v)
            visited.add(v)
            unvisited.remove(v)

        # Collect nearby non-MST pairs as candidates for maze-like loops
        candidate_pairs: list[tuple[float, int, int]] = []
        for i, u in enumerate(room_ids):
            for v in room_ids[i + 1 :]:
                if v in self.adjacency[u]:
                    continue
                if boss_room_id is not None and (u == boss_room_id or v == boss_room_id):
                    continue
                dist = self.room_distance(self.rooms_by_id[u], self.rooms_by_id[v])
                candidate_pairs.append((dist, u, v))

        candidate_pairs.sort(key=lambda item: item[0])
        max_candidates = max(1, len(room_ids) // 2)
        for _, u, v in candidate_pairs[:max_candidates]:
            if rng.random() < extra_loop_chance:
                self.add_edge(u, v)

        return list(self.edges)

    def build_substage_graph(
        self,
        rng: random.Random,
        entrance_id: int,
        shrine_id: int,
        min_mandatory_enemy_rooms: int = 2,
        extra_loop_chance: float = 0.25,
    ) -> list[int]:
        """Build a connected Substage graph guaranteeing >= min_mandatory_enemy_rooms on the route to Shrine.

        Returns the ordered list of room IDs along the mandatory path:
        [entrance_id, mandatory_1, mandatory_2, ..., shrine_id].
        """
        other_ids = [
            rid
            for rid in sorted(self.rooms_by_id.keys())
            if rid not in (entrance_id, shrine_id)
        ]
        entrance_room = self.rooms_by_id[entrance_id]
        shrine_room = self.rooms_by_id[shrine_id]

        # Sort intermediate candidate rooms by distance from entrance toward shrine
        other_ids.sort(
            key=lambda rid: (
                self.room_distance(entrance_room, self.rooms_by_id[rid])
                - 0.35 * self.room_distance(shrine_room, self.rooms_by_id[rid])
            )
        )

        max_mandatory = max(min_mandatory_enemy_rooms, min(3, len(other_ids) - 1))
        mandatory_count = min(
            len(other_ids),
            rng.randint(min_mandatory_enemy_rooms, max_mandatory)
            if max_mandatory >= min_mandatory_enemy_rooms
            else min_mandatory_enemy_rooms,
        )

        # Pick well-spaced rooms along the sorted progression to form the mandatory backbone
        mandatory_chain: list[int] = []
        if mandatory_count > 0 and other_ids:
            for i in range(mandatory_count):
                idx = int(round(i * (len(other_ids) - 1) / max(1, mandatory_count - 1)))
                candidate_id = other_ids[idx]
                if candidate_id not in mandatory_chain:
                    mandatory_chain.append(candidate_id)
            for cid in other_ids:
                if len(mandatory_chain) >= mandatory_count:
                    break
                if cid not in mandatory_chain:
                    mandatory_chain.append(cid)

        mandatory_path = [entrance_id, *mandatory_chain, shrine_id]
        backbone_rank: dict[int, int] = {}
        for rank_idx, rid in enumerate(mandatory_path):
            backbone_rank[rid] = rank_idx
        for i in range(len(mandatory_path) - 1):
            self.add_edge(mandatory_path[i], mandatory_path[i + 1])

        # Attach remaining optional rooms via nearest-neighbor Prim step (excluding shrine_id)
        visited: set[int] = set(mandatory_path)
        unvisited: set[int] = set(self.rooms_by_id.keys()) - visited
        attachable_targets: set[int] = set(mandatory_path[:-1])

        while unvisited:
            best_pair: tuple[int, int] | None = None
            best_dist = float("inf")
            for u in sorted(attachable_targets):
                for v in sorted(unvisited):
                    dist = self.room_distance(self.rooms_by_id[u], self.rooms_by_id[v])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (u, v)

            if best_pair is None:
                break
            u, v = best_pair
            self.add_edge(u, v)
            backbone_rank[v] = backbone_rank[u]
            visited.add(v)
            attachable_targets.add(v)
            unvisited.remove(v)

        # Optional loop edges only between nodes of the same backbone rank so the mandatory
        # enemy rooms can never be bypassed on any path from Entrance to Shrine.
        all_ids = sorted(self.rooms_by_id.keys())
        loop_candidates: list[tuple[float, int, int]] = []
        for i, u in enumerate(all_ids):
            for v in all_ids[i + 1 :]:
                if v in self.adjacency[u]:
                    continue
                if u == shrine_id or v == shrine_id:
                    continue
                if backbone_rank.get(u, -1) != backbone_rank.get(v, -2):
                    continue
                dist = self.room_distance(self.rooms_by_id[u], self.rooms_by_id[v])
                loop_candidates.append((dist, u, v))

        loop_candidates.sort(key=lambda item: item[0])
        for _, u, v in loop_candidates:
            if rng.random() < extra_loop_chance:
                self.add_edge(u, v)

        return mandatory_path

    def bfs_distances(self, start_room_id: int) -> dict[int, int]:
        """Compute shortest hop distances from start_room_id to all reachable rooms."""
        if start_room_id not in self.adjacency:
            return {}

        distances: dict[int, int] = {start_room_id: 0}
        queue: deque[int] = deque([start_room_id])

        while queue:
            current = queue.popleft()
            current_dist = distances[current]
            for neighbor in sorted(self.adjacency[current]):
                if neighbor not in distances:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)

        return distances

    def find_path(self, start_room_id: int, target_room_id: int) -> list[int]:
        """Find shortest room-ID path between two rooms using BFS."""
        if start_room_id not in self.adjacency or target_room_id not in self.adjacency:
            return []

        queue: deque[int] = deque([start_room_id])
        parent: dict[int, int | None] = {start_room_id: None}

        while queue:
            current = queue.popleft()
            if current == target_room_id:
                path: list[int] = []
                node: int | None = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return path

            for neighbor in sorted(self.adjacency[current]):
                if neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)

        return []

    def find_all_simple_paths(
        self,
        start_room_id: int,
        target_room_id: int,
        max_paths: int = 64,
    ) -> list[list[int]]:
        """Return simple paths between start_room_id and target_room_id for route verification."""
        if start_room_id not in self.adjacency or target_room_id not in self.adjacency:
            return []

        results: list[list[int]] = []

        def _dfs(current: int, visited_path: list[int]) -> None:
            if len(results) >= max_paths:
                return
            if current == target_room_id:
                results.append(list(visited_path))
                return
            for neighbor in sorted(self.adjacency[current]):
                if neighbor not in visited_path:
                    visited_path.append(neighbor)
                    _dfs(neighbor, visited_path)
                    visited_path.pop()

        _dfs(start_room_id, [start_room_id])
        return results

    def is_fully_connected(self) -> bool:
        """Return True if every room in the graph is reachable from every other room."""
        if not self.rooms_by_id:
            return True
        first_id = next(iter(self.rooms_by_id))
        distances = self.bfs_distances(first_id)
        return len(distances) == len(self.rooms_by_id)


def find_all_simple_paths(
    graph: DungeonGraph,
    start_room_id: int,
    target_room_id: int,
    max_paths: int = 64,
) -> list[list[int]]:
    """Return simple paths between start_room_id and target_room_id in a DungeonGraph."""
    return graph.find_all_simple_paths(
        start_room_id=start_room_id,
        target_room_id=target_room_id,
        max_paths=max_paths,
    )
