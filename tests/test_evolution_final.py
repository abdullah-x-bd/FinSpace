from __future__ import annotations

import pytest

from finspace import Field, Schema, Space
from finspace.evolution import compare_spaces


def test_append_only_extension_preserves_existing_records() -> None:
    old = Space(Schema(name="versioned", version="1", fields=(Field.enum("x", ("a", "b")),)))
    new = Space(Schema(name="versioned", version="2", fields=(Field.enum("x", ("a", "b", "c")),)))
    migration = compare_spaces(old, new)
    assert migration.mapping == ((0, 0), (1, 1))
    assert migration.added_ranks == (2,)
    assert migration.removed_ranks == ()
    assert migration.rank_churn == 0
    assert migration.migrate_rank(1) == 1


def test_reordering_preserves_objects_while_reporting_rank_churn() -> None:
    old = Space(Schema(name="versioned", version="1", fields=(Field.enum("x", ("a", "b", "c")),)))
    new = Space(Schema(name="versioned", version="2", fields=(Field.enum("x", ("c", "a", "b")),)))
    migration = compare_spaces(old, new)
    assert migration.preserved == 3
    assert migration.rank_churn == 3
    assert migration.rank_churn_fraction == 1.0
    for old_rank, new_rank in migration.mapping:
        assert old.unrank(old_rank) == new.unrank(new_rank)
        assert migration.reverse_rank(new_rank) == old_rank


def test_removed_objects_have_no_migration_target() -> None:
    old = Space(Schema(name="versioned", fields=(Field.enum("x", (1, 2, 3)),)))
    new = Space(Schema(name="versioned", fields=(Field.enum("x", (1, 3)),)))
    migration = compare_spaces(old, new)
    assert migration.removed_ranks == (1,)
    with pytest.raises(KeyError, match="no equivalent"):
        migration.migrate_rank(1)


def test_schema_comparison_has_an_explicit_materialization_cap() -> None:
    old = Space(Schema(name="old", fields=(Field.enum("x", tuple(range(5))),)))
    new = Space(Schema(name="new", fields=(Field.enum("x", tuple(range(5))),)))
    with pytest.raises(ValueError, match="max_objects"):
        compare_spaces(old, new, max_objects=4)
