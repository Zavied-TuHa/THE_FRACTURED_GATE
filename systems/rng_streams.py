"""Deterministic RNG stream hierarchy isolating layout, content, waves, and rewards."""

from __future__ import annotations

import hashlib
import random


def derive_seed(base_seed: int, namespace: str, *indices: int) -> int:
    """Derive a deterministic 64-bit integer seed from base_seed, namespace, and indices."""
    payload = f"{int(base_seed)}:{namespace}:" + ":".join(str(int(i)) for i in indices)
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


class SeedHierarchy:
    """Provides isolated deterministic random.Random streams for a Run."""

    def __init__(self, run_seed: int) -> None:
        self.run_seed: int = int(run_seed)

    def run_rng(self) -> random.Random:
        """Return isolated RNG for run-level decisions (e.g., 3-stage biome order)."""
        return random.Random(derive_seed(self.run_seed, "run", 0))

    def stage_rng(self, stage_index: int = 0) -> random.Random:
        """Return isolated RNG for stage-level decisions."""
        return random.Random(derive_seed(self.run_seed, "stage", stage_index))

    def substage_rng(self, stage_index: int, substage_index: int) -> random.Random:
        """Return isolated RNG for substage parameters (e.g., variable room count)."""
        return random.Random(
            derive_seed(self.run_seed, "substage", stage_index, substage_index)
        )

    def layout_rng(self, stage_index: int, substage_index: int) -> random.Random:
        """Return isolated RNG for room placement, graph edges, and corridor geometry."""
        return random.Random(
            derive_seed(self.run_seed, "layout", stage_index, substage_index)
        )

    def room_content_rng(
        self,
        stage_index: int,
        substage_index: int,
        room_id: int = 0,
    ) -> random.Random:
        """Return isolated RNG for room category distribution and room interior layout."""
        return random.Random(
            derive_seed(
                self.run_seed, "room_content", stage_index, substage_index, room_id
            )
        )

    def enemy_wave_rng(
        self,
        stage_index: int,
        substage_index: int,
        room_id: int,
    ) -> random.Random:
        """Return isolated RNG for enemy wave composition and spawn coordinates."""
        return random.Random(
            derive_seed(
                self.run_seed, "enemy_waves", stage_index, substage_index, room_id
            )
        )

    def object_placement_rng(
        self,
        stage_index: int,
        substage_index: int,
        room_id: int,
    ) -> random.Random:
        """Return isolated RNG for interactive environmental object placement."""
        return random.Random(
            derive_seed(
                self.run_seed, "objects", stage_index, substage_index, room_id
            )
        )

    def reward_rng(
        self,
        stage_index: int,
        substage_index: int,
        room_id: int = 0,
    ) -> random.Random:
        """Return isolated RNG for chest, shrine, and combat drop rewards."""
        return random.Random(
            derive_seed(
                self.run_seed, "rewards", stage_index, substage_index, room_id
            )
        )
