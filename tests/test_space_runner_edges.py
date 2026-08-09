from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from finspace import (
    CheckpointError,
    Condition,
    Field,
    RankOutOfRangeError,
    RecordValidationError,
    Schema,
    Space,
)
from finspace.runner import CheckpointStore, Runner, _default_json


def simple_space() -> Space:
    return Space(
        Schema(
            name="edges",
            fields=(
                Field.enum("kind", ("market", "limit")),
                Field.enum("price", (90, 100), when=(Condition("kind", ("limit",)),)),
                Field.enum("side", ("buy", "sell")),
            ),
        )
    )


def test_partition_helpers_and_space_describe(tmp_path: Path) -> None:
    space = simple_space()
    partition = space.partition(0, 2)
    assert list(partition) == list(range(partition.start, partition.stop))
    assert sum(len(batch) for batch in partition.batches(2)) == len(partition)
    with pytest.raises(ValueError):
        list(partition.batches(0))
    assert partition.to_dict()["count"] == len(partition)
    assert space.describe()["compiled_states"] == space.compilation.states

    path = tmp_path / "space.json"
    space.schema.save(path)
    assert Space.load(path).schema_hash == space.schema_hash


def test_space_record_validation_and_internal_decode_failures() -> None:
    space = simple_space()
    with pytest.raises(RecordValidationError):
        space.rank({"kind": "market", "side": "buy", "unknown": 1})
    with pytest.raises(RecordValidationError):
        space.rank({"kind": "limit", "side": "buy"})
    with pytest.raises(RecordValidationError):
        space.rank({"kind": "limit", "price": 999, "side": "buy"})
    conditioned = space.condition(kind="limit")
    with pytest.raises(RecordValidationError):
        conditioned.rank({"kind": "market", "side": "buy"})

    with pytest.raises(RuntimeError, match="too few tokens"):
        space._record_from_tokens(())
    with pytest.raises(RuntimeError, match="invalid token"):
        space._record_from_tokens(("999", "0"))
    with pytest.raises(RuntimeError, match="trailing tokens"):
        space._record_from_tokens(("0", "0", "0"))


def test_space_boundary_operations() -> None:
    space = simple_space()
    for invalid in (True, -1, space.count, 1.5):
        with pytest.raises(RankOutOfRangeError):
            space.unrank(invalid)  # type: ignore[arg-type]
    assert space.explain(space.unrank(0))["rank"] == 0
    assert len(list(space.enumerate(1, 3))) == 2
    for start, stop in ((-1, None), (3, 2), (0, space.count + 1)):
        with pytest.raises(RankOutOfRangeError):
            list(space.enumerate(start, stop))
    with pytest.raises(ValueError):
        space.sample(-1)
    with pytest.raises(ValueError):
        space.sample(space.count + 1, replace=False)
    assert len(space.sample(10, replace=True, seed=1)) == 10
    assert len(space.unrank_many((0, 1))) == 2
    with pytest.raises(ValueError):
        space.partition(0, 0)
    with pytest.raises(ValueError):
        space.partition(-1, 2)
    with pytest.raises(ValueError):
        space.partition(2, 2)


def test_stratified_sampling_boundaries() -> None:
    space = Space(
        Schema(
            name="strata",
            fields=(Field.enum("group", ("a", "b")), Field.enum("x", (1, 2))),
        )
    )
    sampled = space.sample_stratified("group", 4, seed=5, with_ranks=True)
    assert len(sampled) == 4
    assert {record["group"] for _, record in sampled} == {"a", "b"}
    with pytest.raises(ValueError):
        space.sample_stratified("group", 5, seed=5)


def test_runner_serialization_and_argument_validation(tmp_path: Path) -> None:
    assert _default_json(date(2026, 8, 9)) == "2026-08-09"

    class Item:
        def item(self) -> int:
            return 3

    assert _default_json(Item()) == 3
    with pytest.raises(TypeError):
        _default_json(object())

    space = simple_space()
    with pytest.raises(ValueError):
        Runner(space, lambda record: record, backend="unknown")  # type: ignore[arg-type]
    runner = Runner(space, lambda record: dict(record))
    with pytest.raises(ValueError):
        runner.run(ranks=(0,), partition=space.partition(0, 1))
    with pytest.raises(ValueError):
        runner.run(limit=-1)
    with pytest.raises(ValueError):
        runner.run(ranks=(space.count,))

    checkpoint = tmp_path / "checkpoint.sqlite"
    assert Runner(
        space,
        lambda record: dict(record),
        checkpoint=checkpoint,
        run_id="same",
    ).run(ranks=(0,)).successful
    other_space = Space(Schema(name="other", fields=(Field.enum("x", (1, 2)),)))
    with pytest.raises(CheckpointError):
        Runner(
            other_space,
            lambda record: dict(record),
            checkpoint=checkpoint,
            run_id="same",
        ).run(ranks=(0,))


def test_runner_failure_thread_and_checkpoint_results(tmp_path: Path) -> None:
    space = Space(Schema(name="runner", fields=(Field.enum("x", tuple(range(8))),)))

    def calculate(record: dict[str, object]) -> dict[str, object]:
        if record["x"] == 3:
            raise RuntimeError("deliberate")
        return dict(record)

    checkpoint = tmp_path / "runner.sqlite"
    summary = Runner(
        space,
        calculate,
        backend="thread",
        max_workers=2,
        max_in_flight=2,
        checkpoint=checkpoint,
        run_id="threaded",
    ).run()
    assert summary.failed == 1
    assert not summary.successful
    with CheckpointStore(checkpoint) as store:
        assert len(list(store.results("threaded", "failed"))) == 1
        assert len(store.completed_ranks("threaded")) == 7

    with pytest.raises(RuntimeError, match="deliberate"):
        Runner(space, calculate, fail_fast=True).run(ranks=(3,))
