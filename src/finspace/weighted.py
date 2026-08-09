"""Exact integer-weight sampling over finite FinSpace domains."""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from fractions import Fraction
from typing import TypeAlias

from .schema import JSONValue
from .space import Space

WeightFunction: TypeAlias = Callable[[Mapping[str, JSONValue]], int]
SampledRecord: TypeAlias = dict[str, JSONValue] | tuple[int, dict[str, JSONValue]]


class WeightedSampler:
    """Sample ranks according to exact non-negative integer weights.

    Integer weights avoid floating-point normalization. Replacement draws use an
    integer ticket in ``[0, total_weight)``. Without-replacement draws use the
    same rule after setting each selected object's weight to zero, which gives a
    sequential probability-proportional-to-size sample.

    The sampler materializes one weight per object and is therefore intended for
    bounded domains whose weights genuinely need object-level control. Large
    spaces should prefer stratification or a future compiled weighted scheme.
    """

    def __init__(self, space: Space, weights: Sequence[int]) -> None:
        if len(weights) != space.count:
            raise ValueError(f"expected {space.count} weights, got {len(weights)}")
        normalized: list[int] = []
        for index, weight in enumerate(weights):
            if isinstance(weight, bool) or not isinstance(weight, int) or weight < 0:
                raise ValueError(f"weight for rank {index} must be a non-negative integer")
            normalized.append(weight)
        if not any(normalized):
            raise ValueError("at least one rank must have positive weight")
        self.space = space
        self.weights = tuple(normalized)

    @classmethod
    def from_function(
        cls,
        space: Space,
        function: WeightFunction,
        *,
        max_objects: int = 1_000_000,
    ) -> WeightedSampler:
        if max_objects <= 0:
            raise ValueError("max_objects must be positive")
        if space.count > max_objects:
            raise ValueError(
                f"weighted materialization requires {space.count} objects, above max_objects={max_objects}"
            )
        return cls(space, [function(space.unrank(rank)) for rank in range(space.count)])

    @property
    def total_weight(self) -> int:
        return sum(self.weights)

    @property
    def positive_ranks(self) -> int:
        return sum(weight > 0 for weight in self.weights)

    def probabilities(self) -> tuple[Fraction, ...]:
        total = self.total_weight
        return tuple(Fraction(weight, total) for weight in self.weights)

    @staticmethod
    def _draw(weights: Sequence[int], rng: random.Random) -> int:
        total = sum(weights)
        if total <= 0:
            raise ValueError("no positive weight remains")
        ticket = rng.randrange(total)
        cumulative = 0
        for rank, weight in enumerate(weights):
            cumulative += weight
            if ticket < cumulative:
                return rank
        raise RuntimeError("weighted draw failed despite a positive total")

    def sample(
        self,
        n: int = 1,
        *,
        replace: bool = True,
        seed: int | str | bytes | None = None,
        with_ranks: bool = False,
    ) -> list[SampledRecord]:
        if n < 0:
            raise ValueError("sample size cannot be negative")
        if not replace and n > self.positive_ranks:
            raise ValueError(
                f"cannot draw {n} distinct positive-weight objects from {self.positive_ranks}"
            )
        rng = random.Random(seed)
        working = list(self.weights)
        ranks: list[int] = []
        for _ in range(n):
            rank = self._draw(working if not replace else self.weights, rng)
            ranks.append(rank)
            if not replace:
                working[rank] = 0
        if with_ranks:
            return [(rank, self.space.unrank(rank)) for rank in ranks]
        return [self.space.unrank(rank) for rank in ranks]
