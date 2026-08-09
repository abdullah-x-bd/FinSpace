"""Deterministic rank-allocation strategies for distributed campaigns."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

AllocationStrategy = Literal["contiguous", "strided", "permuted"]


def _seed_bytes(seed: int | str | bytes | None) -> bytes:
    if seed is None:
        return b"0"
    if isinstance(seed, bytes):
        return seed
    return str(seed).encode("utf-8")


def affine_parameters(count: int, seed: int | str | bytes | None = None) -> tuple[int, int]:
    """Return deterministic ``a, b`` for a bijection ``(a*x+b) mod count``.

    The permutation is designed for workload mixing and reproducibility. It is
    not a cryptographic permutation and must not be used as an access-control or
    confidentiality mechanism.
    """

    if count <= 0:
        raise ValueError("count must be positive")
    if count == 1:
        return 0, 0
    digest = hashlib.sha256(_seed_bytes(seed)).digest()
    candidate = int.from_bytes(digest[:16], "big") % count
    if candidate == 0:
        candidate = 1
    while math.gcd(candidate, count) != 1:
        candidate = (candidate + 1) % count
        if candidate == 0:
            candidate = 1
    offset = int.from_bytes(digest[16:], "big") % count
    return candidate, offset


def permute_rank(rank: int, count: int, seed: int | str | bytes | None = None) -> int:
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 0 or rank >= count:
        raise ValueError("rank must satisfy 0 <= rank < count")
    if count == 1:
        return 0
    multiplier, offset = affine_parameters(count, seed)
    return (multiplier * rank + offset) % count


@dataclass(frozen=True)
class RankAllocation:
    """One worker's deterministic view of a global rank interval."""

    schema_hash: str
    count: int
    worker_id: int
    worker_count: int
    strategy: AllocationStrategy = "contiguous"
    seed: int | str | bytes | None = None

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("count must be positive")
        if self.worker_count <= 0:
            raise ValueError("worker_count must be positive")
        if self.worker_id < 0 or self.worker_id >= self.worker_count:
            raise ValueError("worker_id must satisfy 0 <= worker_id < worker_count")
        if self.strategy not in {"contiguous", "strided", "permuted"}:
            raise ValueError(f"unsupported allocation strategy {self.strategy!r}")

    @property
    def start(self) -> int:
        return (self.worker_id * self.count) // self.worker_count

    @property
    def stop(self) -> int:
        return ((self.worker_id + 1) * self.count) // self.worker_count

    def __len__(self) -> int:
        if self.strategy == "strided":
            if self.worker_id >= self.count:
                return 0
            return 1 + (self.count - 1 - self.worker_id) // self.worker_count
        return self.stop - self.start

    def __iter__(self) -> Iterator[int]:
        if self.strategy == "contiguous":
            yield from range(self.start, self.stop)
            return
        if self.strategy == "strided":
            yield from range(self.worker_id, self.count, self.worker_count)
            return
        for logical_rank in range(self.start, self.stop):
            yield permute_rank(logical_rank, self.count, self.seed)

    def to_dict(self) -> dict[str, Any]:
        seed = self.seed.decode("utf-8", errors="backslashreplace") if isinstance(self.seed, bytes) else self.seed
        return {
            "schema_hash": self.schema_hash,
            "count": self.count,
            "worker_id": self.worker_id,
            "worker_count": self.worker_count,
            "strategy": self.strategy,
            "seed": seed,
            "allocation_size": len(self),
        }


def allocations(
    schema_hash: str,
    count: int,
    worker_count: int,
    *,
    strategy: AllocationStrategy = "contiguous",
    seed: int | str | bytes | None = None,
) -> tuple[RankAllocation, ...]:
    return tuple(
        RankAllocation(schema_hash, count, worker, worker_count, strategy, seed)
        for worker in range(worker_count)
    )
