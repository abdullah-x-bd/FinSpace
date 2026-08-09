from __future__ import annotations

from collections import defaultdict

import pytest

from finspace import Condition, Field, RecordValidationError, Schema, Space
from finspace.cluster import build_shard_manifests, execute_shard
from finspace.mutations import invalid_mutations
from finspace.runner import CheckpointStore, Runner


def test_generic_mutations_are_rejected() -> None:
    space = Space(
        Schema(
            name="mutations",
            fields=(
                Field.enum("kind", ("market", "limit")),
                Field.enum("symbol", ("A", "B")),
                Field.enum("price", (10, 20), when=(Condition("kind", ("limit",)),)),
            ),
        )
    )
    market = next(record for record in space.enumerate() if record["kind"] == "market")
    mutations = invalid_mutations(space, market)
    assert any(mutation.label == "inactive-field-price" for mutation in mutations)
    for mutation in mutations:
        with pytest.raises(RecordValidationError):
            space.rank(mutation.record)


def test_cluster_shards_are_portable_and_exact() -> None:
    space = Space(Schema(name="cluster", fields=(Field.enum("x", tuple(range(23))),)))
    shards = build_shard_manifests(space, 5, strategy="permuted", seed=88)
    ranks = [rank for shard in shards for rank in shard.allocation()]
    assert sorted(ranks) == list(range(space.count))
    assert len(set(ranks)) == space.count
    summary = execute_shard(space, lambda record: int(record["x"]) * 2, shards[0])
    assert summary.completed == shards[0].allocation_size
    assert summary.failed == 0


def test_cluster_manifest_rejects_the_wrong_space() -> None:
    first = Space(Schema(name="first", fields=(Field.enum("x", (1, 2)),)))
    second = Space(Schema(name="second", fields=(Field.enum("x", (1, 2)),)))
    shard = build_shard_manifests(first, 1)[0]
    with pytest.raises(ValueError, match="does not match"):
        execute_shard(second, lambda record: record, shard)


def test_transient_failure_is_retried_and_recorded(tmp_path) -> None:
    space = Space(Schema(name="retry", fields=(Field.enum("x", (0, 1, 2)),)))
    calls: defaultdict[int, int] = defaultdict(int)

    def flaky(record):
        value = int(record["x"])
        calls[value] += 1
        if calls[value] == 1:
            raise RuntimeError("transient")
        return value

    checkpoint = tmp_path / "retry.sqlite"
    summary = Runner(
        space,
        flaky,
        checkpoint=checkpoint,
        run_id="retry",
        max_retries=1,
    ).run()
    assert summary.completed == 3
    assert summary.failed == 0
    assert summary.retries == 3
    with CheckpointStore(checkpoint) as store:
        assert store.failed_ranks("retry") == set()
        assert store.status_counts("retry") == {"completed": 3}
        assert {result.attempts for result in store.results("retry")} == {2}


def test_failed_rank_remains_retryable_on_a_later_run(tmp_path) -> None:
    space = Space(Schema(name="retry-later", fields=(Field.enum("x", (0, 1)),)))
    checkpoint = tmp_path / "later.sqlite"
    first = Runner(
        space,
        lambda _: (_ for _ in ()).throw(RuntimeError("hard failure")),
        checkpoint=checkpoint,
        run_id="later",
        max_retries=1,
    ).run(ranks=[0])
    assert first.failed == 1
    assert first.retries == 1
    with CheckpointStore(checkpoint) as store:
        assert store.failed_ranks("later") == {0}
    second = Runner(
        space,
        lambda record: int(record["x"]),
        checkpoint=checkpoint,
        run_id="later",
    ).run(ranks=[0, 1])
    assert second.completed == 2
    assert second.skipped == 0
