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
        self.adjacency: dict[int, set[int]] = {r.room_id: set() for r in self.rooms_by_id.values()}
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

    def is_fully_connected(self) -> bool:
        """Return True if every room in the graph is reachable from every other room."""
        if not self.rooms_by_id:
            return True
        first_id = next(iter(self.rooms_by_id))
        distances = self.bfs_distances(first_id)
        return len(distances) == len(self.rooms_by_id)
