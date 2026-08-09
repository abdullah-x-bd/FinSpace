from __future__ import annotations

import pytest

from finspace import Field, Schema, Space
from finspace.identity import create_rank_handle, parse_rank_handle
from finspace.shrink import shrink_failure


def _space() -> Space:
    return Space(Schema(name="shrink-handle", fields=(Field.enum("value", tuple(range(20))),)))


def test_shrinker_finds_earliest_failure_in_canonical_rank_order() -> None:
    space = _space()
    result = shrink_failure(space, 18, lambda record: int(record["value"]) >= 7)
    assert result.shrunk_rank == 7
    assert result.complete_search
    assert result.changed


def test_shrinker_reports_incomplete_budget_and_rejects_nonfailure() -> None:
    space = _space()
    result = shrink_failure(
        space,
        18,
        lambda record: int(record["value"]) >= 17,
        max_evaluations=5,
    )
    assert result.shrunk_rank == 18
    assert not result.complete_search
    with pytest.raises(ValueError, match="does not satisfy"):
        shrink_failure(space, 3, lambda record: int(record["value"]) >= 7)


def test_checksum_handle_roundtrip_and_tamper_detection() -> None:
    space = _space()
    handle = create_rank_handle(space, 9)
    encoded = handle.encode()
    parsed = parse_rank_handle(encoded)
    assert parsed == handle
    assert parsed.verify(space)
    tampered = parse_rank_handle(encoded.replace(".9.", ".8."))
    assert not tampered.verify(space)


def test_mac_handle_requires_the_same_secret_key() -> None:
    space = _space()
    handle = create_rank_handle(space, 4, key=b"correct-secret")
    assert handle.verify(space, key=b"correct-secret")
    assert not handle.verify(space, key=b"wrong-secret")
    assert not handle.verify(space)


@pytest.mark.parametrize(
    "value",
    ["garbage", "fs1.short.1.checksum.abc", "fs1." + "0" * 64 + ".x.checksum.abc"],
)
def test_malformed_handles_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        parse_rank_handle(value)
