"""Exact compatibility maps between bounded FinSpace schema versions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .replay import canonical_json
from .space import Space


@dataclass(frozen=True)
class MigrationMap:
    """Record-preserving rank map between two exact schema versions.

    Dense ranks are intentionally schema-relative. This object does not claim to
    preserve rank numbers after arbitrary edits. Instead, it records which
    canonical records survive an edit and where those records move.
    """

    old_schema_hash: str
    new_schema_hash: str
    old_count: int
    new_count: int
    mapping: tuple[tuple[int, int], ...]
    removed_ranks: tuple[int, ...]
    added_ranks: tuple[int, ...]

    @property
    def preserved(self) -> int:
        return len(self.mapping)

    @property
    def stable_ranks(self) -> int:
        return sum(old == new for old, new in self.mapping)

    @property
    def rank_churn(self) -> int:
        return self.preserved - self.stable_ranks

    @property
    def rank_churn_fraction(self) -> float:
        if self.preserved == 0:
            return 0.0
        return self.rank_churn / self.preserved

    def migrate_rank(self, old_rank: int) -> int:
        for source, target in self.mapping:
            if source == old_rank:
                return target
        raise KeyError(f"old rank {old_rank} has no equivalent object in the new schema")

    def reverse_rank(self, new_rank: int) -> int:
        for source, target in self.mapping:
            if target == new_rank:
                return source
        raise KeyError(f"new rank {new_rank} has no equivalent object in the old schema")

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_schema_hash": self.old_schema_hash,
            "new_schema_hash": self.new_schema_hash,
            "old_count": self.old_count,
            "new_count": self.new_count,
            "preserved": self.preserved,
            "stable_ranks": self.stable_ranks,
            "rank_churn": self.rank_churn,
            "rank_churn_fraction": self.rank_churn_fraction,
            "mapping": [{"old_rank": old, "new_rank": new} for old, new in self.mapping],
            "removed_ranks": list(self.removed_ranks),
            "added_ranks": list(self.added_ranks),
        }


def compare_spaces(old: Space, new: Space, *, max_objects: int = 1_000_000) -> MigrationMap:
    """Build an exact compatibility map by canonical record equality.

    This bounded algorithm intentionally refuses to materialize arbitrarily large
    domains. It is a migration/audit tool, not part of rank/unrank hot paths.
    """

    if max_objects <= 0:
        raise ValueError("max_objects must be positive")
    if old.count > max_objects or new.count > max_objects:
        raise ValueError(
            "schema comparison would exceed max_objects; narrow the domain or raise the explicit cap"
        )

    new_by_record: dict[bytes, int] = {}
    for new_rank in range(new.count):
        key = canonical_json(new.unrank(new_rank))
        if key in new_by_record:
            raise ValueError("new schema contains duplicate canonical records")
        new_by_record[key] = new_rank

    mapping: list[tuple[int, int]] = []
    removed: list[int] = []
    mapped_new: set[int] = set()
    for old_rank in range(old.count):
        key = canonical_json(old.unrank(old_rank))
        matched_rank = new_by_record.get(key)
        if matched_rank is None:
            removed.append(old_rank)
        else:
            mapping.append((old_rank, matched_rank))
            mapped_new.add(matched_rank)

    added = tuple(rank for rank in range(new.count) if rank not in mapped_new)
    return MigrationMap(
        old_schema_hash=old.schema_hash,
        new_schema_hash=new.schema_hash,
        old_count=old.count,
        new_count=new.count,
        mapping=tuple(mapping),
        removed_ranks=tuple(removed),
        added_ranks=added,
    )
