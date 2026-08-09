from __future__ import annotations

import pytest

from finspace import Condition, Field, RecordValidationError, Schema, SchemaDefinitionError, Space


def test_large_logical_domain_compiles_without_materialization() -> None:
    schema = Schema(
        name="large-shared-suffix",
        fields=(
            Field.enum("currency", tuple(f"C{i}" for i in range(100))),
            Field.enum("spot_bucket", tuple(range(100))),
            Field.enum("strike_bucket", tuple(range(100))),
            Field.enum("maturity_bucket", tuple(range(100))),
        ),
    )
    space = Space(schema)
    assert space.count == 100**4
    assert space.compilation.states < 1000
    for rank in (0, 1, space.count // 2, space.count - 1):
        assert space.rank(space.unrank(rank)) == rank


def test_highly_asymmetric_dependency_map_remains_exact() -> None:
    mapping = {
        "tiny": (1,),
        "small": tuple(range(3)),
        "medium": tuple(range(20)),
        "large": tuple(range(200)),
    }
    space = Space(
        Schema(
            name="asymmetric",
            fields=(
                Field.enum("branch", tuple(mapping)),
                Field.dependent("value", "branch", mapping),
                Field.enum("side", ("buy", "sell")),
            ),
        )
    )
    assert space.count == 2 * sum(len(values) for values in mapping.values())
    for rank in (0, 1, 2, space.count // 2, space.count - 1):
        record = space.unrank(rank)
        assert record["value"] in mapping[record["branch"]]
        assert space.rank(record) == rank


def test_multiple_inactive_fields_are_not_serialized_into_records() -> None:
    space = Space(
        Schema(
            name="conditional-chain",
            fields=(
                Field.enum("kind", ("market", "limit", "stop_limit")),
                Field.enum(
                    "price",
                    (90, 100),
                    when=(Condition("kind", ("limit", "stop_limit")),),
                ),
                Field.enum(
                    "stop_price",
                    (80, 85),
                    when=(Condition("kind", ("stop_limit",)),),
                ),
                Field.enum("venue", ("A", "B")),
            ),
        )
    )
    for record in space.enumerate():
        if record["kind"] == "market":
            assert "price" not in record
            assert "stop_price" not in record
        elif record["kind"] == "limit":
            assert "price" in record
            assert "stop_price" not in record
        else:
            assert "price" in record
            assert "stop_price" in record


def test_impossible_conditioning_fails_loudly() -> None:
    space = Space(Schema(name="condition", fields=(Field.enum("currency", ("USD", "EUR")),)))
    with pytest.raises(SchemaDefinitionError):
        space.condition(currency="JPY")


def test_dependent_value_from_wrong_branch_is_rejected() -> None:
    space = Space(
        Schema(
            name="rates",
            fields=(
                Field.enum("currency", ("USD", "EUR")),
                Field.dependent(
                    "rate",
                    "currency",
                    {"USD": (1, 2, 3), "EUR": (-1, 0)},
                ),
            ),
        )
    )
    with pytest.raises(RecordValidationError):
        space.rank({"currency": "EUR", "rate": 3})


def test_dependency_cannot_reference_a_later_field() -> None:
    with pytest.raises(SchemaDefinitionError):
        Schema(
            name="invalid-order",
            fields=(
                Field.dependent("rate", "currency", {"USD": (1,)}),
                Field.enum("currency", ("USD",)),
            ),
        )
