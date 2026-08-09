"""Deterministic shrinking of failing FinSpace objects."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .schema import JSONValue
from .space import Space

FailurePredicate = Callable[[Mapping[str, JSONValue]], bool]


@dataclass(frozen=True)
class ShrinkResult:
    original_rank: int
    shrunk_rank: int
    evaluations: int
    complete_search: bool

    @property
    def changed(self) -> bool:
        return self.original_rank != self.shrunk_rank

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_rank": self.original_rank,
            "shrunk_rank": self.shrunk_rank,
            "evaluations": self.evaluations,
            "complete_search": self.complete_search,
            "changed": self.changed,
        }


def shrink_failure(
    space: Space,
    failing_rank: int,
    predicate: FailurePredicate,
    *,
    max_evaluations: int = 10_000,
) -> ShrinkResult:
    """Find the earliest failing rank within a deterministic search budget.

    Rank order is a canonical order for a fixed schema, so this gives FinSpace a
    reproducible baseline shrinker even when no domain-specific notion of
    structural size is available. If the whole prefix is searched, the result is
    the globally smallest failing rank under that canonical order.
    """

    if max_evaluations <= 0:
        raise ValueError("max_evaluations must be positive")
    original = space.unrank(failing_rank)
    evaluations = 1
    if not predicate(original):
        raise ValueError("failing_rank does not satisfy the failure predicate")

    candidate_limit = min(failing_rank, max_evaluations - 1)
    for candidate_rank in range(candidate_limit):
        evaluations += 1
        if predicate(space.unrank(candidate_rank)):
            return ShrinkResult(
                original_rank=failing_rank,
                shrunk_rank=candidate_rank,
                evaluations=evaluations,
                complete_search=True,
            )

    complete = candidate_limit == failing_rank
    return ShrinkResult(
        original_rank=failing_rank,
        shrunk_rank=failing_rank,
        evaluations=evaluations,
        complete_search=complete,
    )
