"""Generic invalid-record mutations for adversarial FinSpace testing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import Field, JSONValue, _canonical
from .space import Space


@dataclass(frozen=True)
class RecordMutation:
    label: str
    record: dict[str, JSONValue]

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "record": dict(self.record)}


def _declared_values(field: Field) -> tuple[JSONValue, ...]:
    values: list[JSONValue] = []
    if field.values is not None:
        values.extend(field.values)
    for case in field.cases:
        values.extend(case.values)
    if field.default is not None:
        values.extend(field.default)
    unique: dict[str, JSONValue] = {}
    for value in values:
        unique[_canonical(value)] = value
    return tuple(unique.values())


def _invalid_value(field: Field) -> JSONValue:
    declared = {_canonical(value) for value in _declared_values(field)}
    candidates: tuple[JSONValue, ...] = (
        "__FINSPACE_INVALID__",
        9_223_372_036_854_775_807,
        -9_223_372_036_854_775_808,
        1.7976931348623157e308,
        None,
        True,
        False,
    )
    for candidate in candidates:
        if _canonical(candidate) not in declared:
            return candidate
    raise ValueError(f"could not construct an invalid value for field {field.name!r}")


def invalid_mutations(space: Space, record: dict[str, JSONValue]) -> tuple[RecordMutation, ...]:
    """Generate deterministic invalid variants of one valid canonical record."""

    space.validate(record)
    output: list[RecordMutation] = []

    unknown = dict(record)
    unknown["__finspace_unknown__"] = "invalid"
    output.append(RecordMutation("unknown-field", unknown))

    for field in space.schema.fields:
        if field.name in record:
            missing = dict(record)
            missing.pop(field.name)
            output.append(RecordMutation(f"missing-{field.name}", missing))

            wrong = dict(record)
            wrong[field.name] = _invalid_value(field)
            output.append(RecordMutation(f"invalid-value-{field.name}", wrong))
        else:
            declared = _declared_values(field)
            if declared:
                inactive = dict(record)
                inactive[field.name] = declared[0]
                output.append(RecordMutation(f"inactive-field-{field.name}", inactive))

    deduplicated: dict[bytes, RecordMutation] = {}
    for mutation in output:
        key = repr(sorted(mutation.record.items())).encode()
        deduplicated.setdefault(key, mutation)
    return tuple(deduplicated.values())
