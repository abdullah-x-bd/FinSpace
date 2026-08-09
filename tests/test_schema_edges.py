from __future__ import annotations

import json
from pathlib import Path

import pytest

from finspace import Case, Condition, Field, Schema, SchemaDefinitionError


def test_schema_primitives_reject_invalid_definitions() -> None:
    invalid_builders = (
        lambda: Condition("", (1,)),
        lambda: Condition("x", ()),
        lambda: Case("a", ()),
        lambda: Field.enum("bad-name", (1,)),
        lambda: Field(name="x"),
        lambda: Field(name="x", values=(1,), cases=(Case(1, (2,)),)),
        lambda: Field(name="x", values=(1,), depends_on="y", cases=(Case(1, (2,)),)),
        lambda: Field(name="x", depends_on="y"),
        lambda: Field(name="x", depends_on="y", cases=(Case(1, (2,)), Case(1, (3,)))),
        lambda: Field.integer("x", 2, 1),
        lambda: Field.integer("x", 1, 2, step=0),
    )
    for builder in invalid_builders:
        with pytest.raises(SchemaDefinitionError):
            builder()


def test_schema_values_must_be_unique_finite_json() -> None:
    with pytest.raises(SchemaDefinitionError):
        Field.enum("x", (1, 1))
    with pytest.raises(SchemaDefinitionError):
        Field.enum("x", (float("nan"),))
    with pytest.raises(SchemaDefinitionError):
        Schema(name="meta", fields=(Field.enum("x", (1,)),), metadata={"bad": float("inf")})


def test_conditions_and_dependent_defaults_cover_resolution_paths() -> None:
    condition = Condition("kind", ("limit",))
    assert not condition.matches({})
    assert condition.matches({"kind": "limit"})
    assert not condition.matches({"kind": "market"})
    field = Field.dependent(
        "rate",
        "currency",
        {"USD": (1, 2)},
        default=(0,),
        when=(Condition("enabled", (True,)),),
    )
    assert field.resolve_values({"enabled": False}) == ()
    with pytest.raises(SchemaDefinitionError):
        field.resolve_values({"enabled": True})
    assert field.resolve_values({"enabled": True, "currency": "USD"}) == (1, 2)
    assert field.resolve_values({"enabled": True, "currency": "EUR"}) == (0,)
    assert field.dependencies() == {"enabled", "currency"}


def test_field_dict_forms_roundtrip_mapping_and_sequence_cases() -> None:
    unconditional = Field.from_dict(
        {
            "name": "side",
            "values": ["buy", "sell"],
            "when": {"enabled": True},
            "description": "trade side",
        }
    )
    assert unconditional.when[0] == Condition("enabled", (True,))
    dependent_mapping = Field.from_dict(
        {
            "name": "rate",
            "depends_on": "currency",
            "cases": {"USD": [1, 2], "EUR": [0]},
            "default": [-1],
        }
    )
    dependent_sequence = Field.from_dict(
        {
            "name": "rate",
            "depends_on": "currency",
            "cases": [
                {"equals": "USD", "values": [1, 2]},
                {"equals": "EUR", "values": [0]},
            ],
        }
    )
    assert dependent_mapping.to_dict()["default"] == [-1]
    assert dependent_sequence.resolve_values({"currency": "USD"}) == (1, 2)


def test_schema_container_validation_and_lookup_errors() -> None:
    with pytest.raises(SchemaDefinitionError):
        Schema(name="", fields=(Field.enum("x", (1,)),))
    with pytest.raises(SchemaDefinitionError):
        Schema(name="empty", fields=())
    with pytest.raises(SchemaDefinitionError):
        Schema(name="dup", fields=(Field.enum("x", (1,)), Field.enum("x", (2,))))

    schema = Schema(
        name="lookup",
        fields=(
            Field.enum("kind", ("a", "b")),
            Field.enum("conditional", (1,), when=(Condition("kind", ("a",)),)),
        ),
        description="demo",
        metadata={"source": "test"},
    )
    assert schema.field("kind").name == "kind"
    with pytest.raises(SchemaDefinitionError):
        schema.field("unknown")
    with pytest.raises(SchemaDefinitionError):
        schema.possible_values("conditional")
    payload = schema.to_dict()
    assert payload["description"] == "demo"
    assert payload["metadata"] == {"source": "test"}
    assert Schema.from_dict(payload).hash == schema.hash
    assert "kind" in schema.relevant_context()[1]


def test_schema_save_load_json_yaml_and_non_object(tmp_path: Path) -> None:
    schema = Schema(name="io", fields=(Field.enum("x", (1, 2)),))
    json_path = tmp_path / "schema.json"
    yaml_path = tmp_path / "schema.yaml"
    schema.save(json_path)
    schema.save(yaml_path)
    assert Schema.load(json_path).hash == schema.hash
    assert Schema.load(yaml_path).hash == schema.hash

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(SchemaDefinitionError):
        Schema.load(bad)
