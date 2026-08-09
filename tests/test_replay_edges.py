from __future__ import annotations

from pathlib import Path

import pytest

from finspace import (
    CANONICALIZATION_VERSION,
    ExecutionIdentity,
    Field,
    ObjectIdentity,
    ReplayLedger,
    Schema,
    Space,
    build_execution_identity,
    build_object_identity,
)
from finspace.replay import package_version


def replay_space() -> Space:
    return Space(Schema(name="replay-edges", fields=(Field.enum("x", (1, 2, 3)),)))


def test_object_and_execution_identity_validation_errors() -> None:
    good_hash = "0" * 64
    invalid_objects = (
        ObjectIdentity("", good_hash, 0, "0.2"),
        ObjectIdentity(CANONICALIZATION_VERSION, "bad", 0, "0.2"),
        ObjectIdentity(CANONICALIZATION_VERSION, good_hash, -1, "0.2"),
        ObjectIdentity(CANONICALIZATION_VERSION, good_hash, True, "0.2"),
        ObjectIdentity(CANONICALIZATION_VERSION, good_hash, 0, ""),
    )
    for identity in invalid_objects:
        with pytest.raises(ValueError):
            _ = identity.identity_hash

    execution = ExecutionIdentity(
        object_identity_hash="",
        finspace_version="0.1",
        finspace_commit=None,
        adapter_name="reference",
        adapter_version="1",
        environment_hash=good_hash,
        oracle_config_hash=good_hash,
        external_data_snapshot=None,
        execution_parameters_hash=good_hash,
    )
    with pytest.raises(ValueError, match="object_identity_hash"):
        _ = execution.identity_hash


def test_replay_unknown_identity_states(tmp_path: Path) -> None:
    space = replay_space()
    with ReplayLedger(tmp_path / "unknown.sqlite") as ledger:
        assert ledger.verify_object(space, "missing") == "unknown-object"
        assert (
            ledger.verify_execution(
                "missing",
                adapter_name="a",
                adapter_version="1",
                environment={},
                oracle_config={},
                execution_parameters={},
                external_data_snapshot=None,
            )
            == "unknown-execution"
        )
        with pytest.raises(KeyError):
            ledger.get_object("missing")
        with pytest.raises(KeyError):
            ledger.get_execution("missing")


def test_replay_object_reports_canonical_schema_and_digest_mismatches(tmp_path: Path) -> None:
    space = replay_space()
    with ReplayLedger(tmp_path / "objects.sqlite") as ledger:
        old_identity = ObjectIdentity(
            canonicalization_version="1",
            schema_hash=space.schema_hash,
            rank=0,
            pdrs_version="0.2.0",
        )
        old_hash = ledger.record_object(old_identity, space.unrank(0))
        assert ledger.verify_object(space, old_hash) == "canonicalization-version-mismatch"

        valid_identity = build_object_identity(space, 1)
        valid_hash = ledger.record_object(valid_identity, space.unrank(1))
        other_space = Space(Schema(name="other", fields=(Field.enum("y", (1, 2)),)))
        assert ledger.verify_object(other_space, valid_hash) == "schema-mismatch"

        wrong_record_identity = build_object_identity(space, 2)
        wrong_record_hash = ledger.record_object(wrong_record_identity, {"x": 999})
        assert ledger.verify_object(space, wrong_record_hash) == "object-digest-mismatch"


def test_record_execution_rejects_hash_inconsistency(tmp_path: Path) -> None:
    space = replay_space()
    environment = {"python": "3.12"}
    oracle = {"name": "ref"}
    parameters = {"workers": 1}
    with ReplayLedger(tmp_path / "execution.sqlite") as ledger:
        object_hash = ledger.record_object(build_object_identity(space, 0), space.unrank(0))
        identity = build_execution_identity(
            object_hash,
            adapter_name="ref",
            adapter_version="1",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
        )
        with pytest.raises(ValueError, match="environment_hash"):
            ledger.record_execution(
                identity,
                environment={"python": "different"},
                oracle_config=oracle,
                execution_parameters=parameters,
            )
        with pytest.raises(ValueError, match="oracle_config_hash"):
            ledger.record_execution(
                identity,
                environment=environment,
                oracle_config={"name": "other"},
                execution_parameters=parameters,
            )
        with pytest.raises(ValueError, match="execution_parameters_hash"):
            ledger.record_execution(
                identity,
                environment=environment,
                oracle_config=oracle,
                execution_parameters={"workers": 2},
            )


def test_export_manifest_and_package_fallback(tmp_path: Path) -> None:
    space = replay_space()
    environment = {"python": "3.12"}
    oracle = {"name": "ref"}
    parameters = {"workers": 1}
    with ReplayLedger(tmp_path / "manifest.sqlite") as ledger:
        object_hash = ledger.record_object(build_object_identity(space, 0), space.unrank(0))
        identity = build_execution_identity(
            object_hash,
            adapter_name="ref",
            adapter_version="1",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
        )
        execution_hash = ledger.record_execution(
            identity,
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            result={"value": 1},
        )
        manifest = ledger.export_manifest(execution_hash)
        assert manifest["object"]["rank"] == 0
        assert manifest["execution"]["status"] == "completed"
    assert package_version("finspace-package-that-does-not-exist", "fallback") == "fallback"
