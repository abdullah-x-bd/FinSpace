"""Cluster-neutral shard manifests for Ray, Dask, Spark, and batch schedulers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from .allocation import AllocationStrategy, RankAllocation
from .runner import Backend, RunSummary, Runner
from .space import Space


@dataclass(frozen=True)
class ShardManifest:
    manifest_version: str
    schema_hash: str
    engine_hash: str
    object_count: int
    worker_id: int
    worker_count: int
    strategy: AllocationStrategy
    seed: int | str | bytes | None
    allocation_size: int

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if isinstance(self.seed, bytes):
            result["seed"] = self.seed.decode("utf-8", errors="backslashreplace")
        return result

    def allocation(self) -> RankAllocation:
        return RankAllocation(
            self.schema_hash,
            self.object_count,
            self.worker_id,
            self.worker_count,
            self.strategy,
            self.seed,
        )

    def validate_space(self, space: Space) -> bool:
        return (
            self.schema_hash == space.schema_hash
            and self.engine_hash == space.engine_hash
            and self.object_count == space.count
        )


def build_shard_manifests(
    space: Space,
    worker_count: int,
    *,
    strategy: AllocationStrategy = "contiguous",
    seed: int | str | bytes | None = None,
) -> tuple[ShardManifest, ...]:
    if worker_count <= 0:
        raise ValueError("worker_count must be positive")
    output: list[ShardManifest] = []
    for worker_id in range(worker_count):
        allocation = RankAllocation(
            space.schema_hash,
            space.count,
            worker_id,
            worker_count,
            strategy,
            seed,
        )
        output.append(
            ShardManifest(
                manifest_version="1",
                schema_hash=space.schema_hash,
                engine_hash=space.engine_hash,
                object_count=space.count,
                worker_id=worker_id,
                worker_count=worker_count,
                strategy=strategy,
                seed=seed,
                allocation_size=len(allocation),
            )
        )
    return tuple(output)


def execute_shard(
    space: Space,
    function: Callable[[Mapping[str, Any]], Any],
    shard: ShardManifest,
    *,
    backend: Backend = "sequential",
    max_workers: int | None = None,
    checkpoint: str | None = None,
    run_id: str | None = None,
    max_retries: int = 0,
) -> RunSummary:
    """Execute one portable shard through the ordinary checkpointed Runner."""

    if not shard.validate_space(space):
        raise ValueError("shard manifest does not match this FinSpace space")
    allocation = shard.allocation()
    return Runner(
        space,
        function,
        backend=backend,
        max_workers=max_workers,
        checkpoint=checkpoint,
        run_id=run_id or f"shard-{shard.worker_id}-of-{shard.worker_count}",
        max_retries=max_retries,
    ).run(ranks=allocation)
