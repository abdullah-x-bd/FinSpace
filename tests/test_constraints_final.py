from __future__ import annotations

import pytest

from finspace import Field, RecordValidationError, Schema, SchemaDefinitionError, Space
from finspace.schema import TableConstraint


def test_table_constraint_prunes_cartesian_domain_exactly() -> None:
    schema = Schema(
        name="currency-engine",
        fields=(
            Field.enum("currency", ("USD", "EUR", "JPY")),
            Field.enum("engine", ("analytic", "fd", "tree")),
        ),
        constraints=(
            TableConstraint(
                ("currency", "engine"),
                (("USD", "analytic"), ("USD", "fd"), ("EUR", "analytic"), ("JPY", "tree")),
            ),
        ),
    )
    space = Space(schema)
    assert space.count == 4
    records = list(space.enumerate())
    assert {tuple(record.values()) for record in records} == {
        ("USD", "analytic"),
        ("USD", "fd"),
        ("EUR", "analytic"),
        ("JPY", "tree"),
    }
    for rank, record in enumerate(records):
        assert space.rank(record) == rank
        assert space.unrank(rank) == record
    with pytest.raises(RecordValidationError, match="table constraint"):
        space.rank({"currency": "EUR", "engine": "tree"})


def test_constraint_roundtrip_is_hash_stable() -> None:
    original = Schema(
        name="constraint-roundtrip",
        fields=(Field.enum("x", (1, 2)), Field.enum("y", ("a", "b"))),
        constraints=(TableConstraint(("x", "y"), ((1, "a"), (2, "b"))),),
    )
    restored = Schema.from_dict(original.to_dict())
    assert restored == original
    assert restored.hash == original.hash
    assert Space(restored).count == 2


def test_conditioning_can_reduce_a_constrained_space() -> None:
    schema = Schema(
        name="conditioned-constraint",
        fields=(Field.enum("x", (1, 2)), Field.enum("y", ("a", "b"))),
        constraints=(TableConstraint(("x", "y"), ((1, "a"), (2, "b"))),),
    )
    assert Space(schema).condition(x=1).count == 1
    with pytest.raises(SchemaDefinitionError, match="empty domain"):
        Space(schema).condition(x=1, y="b")


@pytest.mark.parametrize(
    "constraint",
    [
        TableConstraint,
    ],
)
def test_constraint_constructor_symbol_is_publicly_importable(constraint: object) -> None:
    assert constraint is TableConstraint


def test_malformed_constraints_are_rejected() -> None:
    with pytest.raises(SchemaDefinitionError, match="at least two"):
        TableConstraint(("x",), ((1,),))
    with pytest.raises(SchemaDefinitionError, match="exactly one value"):
        TableConstraint(("x", "y"), ((1,),))
    with pytest.raises(SchemaDefinitionError, match="duplicate allowed"):
        TableConstraint(("x", "y"), ((1, 2), (1, 2)))
    with pytest.raises(SchemaDefinitionError, match="unknown fields"):
        Schema(
            name="bad",
            fields=(Field.enum("x", (1, 2)), Field.enum("y", (1, 2))),
            constraints=(TableConstraint(("x", "z"), ((1, 2),)),),
        )
