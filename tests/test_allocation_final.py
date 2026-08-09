from __future__ import annotations

import pytest

from finspace import Field, Schema, Space
from finspace.allocation import RankAllocation, allocations, permute_rank


def _space(count: int = 37) -> Space:
    return Space(Schema(name="allocation", fields=(Field.enum("value", tuple(range(count))),)))


@pytest.mark.parametrize("strategy", ["contiguous", "strided", "permuted"])
@pytest.mark.parametrize("workers", [1, 2, 3, 7, 16, 64])
def test_allocations_form_an_exact_partition(strategy: str, workers: int) -> None:
    space = _space()
    shards = allocations(space.schema_hash, space.count, workers, strategy=strategy, seed=123)  # type: ignore[arg-type]
    observed = [rank for shard in shards for rank in shard]
    assert len(observed) == space.count
    assert len(set(observed)) == space.count
    assert sorted(observed) == list(range(space.count))
    sizes = [len(shard) for shard in shards]
    assert max(sizes) - min(sizes) <= 1


def test_permutation_is_seeded_bijective_and_changes_with_seed() -> None:
    count = 101
    first = [permute_rank(rank, count, "alpha") for rank in range(count)]
    same = [permute_rank(rank, count, "alpha") for rank in range(count)]
    other = [permute_rank(rank, count, "beta") for rank in range(count)]
    assert first == same
    assert sorted(first) == list(range(count))
    assert first != other


def test_allocation_validation() -> None:
    space = _space()
    with pytest.raises(ValueError, match="worker_count"):
        RankAllocation(space.schema_hash, space.count, 0, 0)
    with pytest.raises(ValueError, match="worker_id"):
        RankAllocation(space.schema_hash, space.count, 2, 2)
    with pytest.raises(ValueError, match="unsupported"):
        RankAllocation(space.schema_hash, space.count, 0, 1, "unknown")  # type: ignore[arg-type]
