from __future__ import annotations

from fractions import Fraction

import pytest

from finspace import Field, Schema, Space
from finspace.weighted import WeightedSampler


def _space() -> Space:
    return Space(Schema(name="weighted", fields=(Field.enum("value", ("a", "b", "c")),)))


def test_exact_probabilities_and_seeded_sampling() -> None:
    sampler = WeightedSampler(_space(), (1, 3, 6))
    assert sampler.total_weight == 10
    assert sampler.positive_ranks == 3
    assert sampler.probabilities() == (Fraction(1, 10), Fraction(3, 10), Fraction(3, 5))
    first = sampler.sample(100, seed=42, with_ranks=True)
    second = sampler.sample(100, seed=42, with_ranks=True)
    assert first == second


def test_zero_weight_is_never_drawn() -> None:
    sampler = WeightedSampler(_space(), (0, 1, 0))
    draws = sampler.sample(50, seed=7, with_ranks=True)
    assert {rank for rank, _ in draws} == {1}


def test_without_replacement_is_unique_and_weight_limited() -> None:
    sampler = WeightedSampler(_space(), (4, 0, 2))
    draws = sampler.sample(2, replace=False, seed=9, with_ranks=True)
    assert len({rank for rank, _ in draws}) == 2
    assert {rank for rank, _ in draws} == {0, 2}
    with pytest.raises(ValueError, match="distinct positive-weight"):
        sampler.sample(3, replace=False)


def test_from_function_and_materialization_cap() -> None:
    space = _space()
    sampler = WeightedSampler.from_function(
        space, lambda record: {"a": 1, "b": 2, "c": 3}[str(record["value"])]
    )
    assert sampler.weights == (1, 2, 3)
    with pytest.raises(ValueError, match="above max_objects"):
        WeightedSampler.from_function(space, lambda _: 1, max_objects=2)


@pytest.mark.parametrize("weights", [(1, 2), (0, 0, 0), (1, -1, 2), (1, True, 2)])
def test_invalid_weight_vectors_are_rejected(weights: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        WeightedSampler(_space(), weights)  # type: ignore[arg-type]
