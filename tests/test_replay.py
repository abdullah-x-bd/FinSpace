from __future__ import annotations

import tempfile
from pathlib import Path

from finspace.replay import (
    CANONICALIZATION_VERSION,
    ReplayLedger,
    build_execution_identity,
    build_object_identity,
    digest,
    environment_manifest,
)


class FakeSpace:
    schema_hash = "a" * 64

    def unrank(self, rank: int):
        return {"kind": "case", "rank": rank}


def test_object_and_execution_replay_are_separate() -> None:
    space = FakeSpace()
    with (
        tempfile.TemporaryDirectory() as directory,
        ReplayLedger(Path(directory) / "ledger.sqlite") as ledger,
    ):
        object_identity = build_object_identity(space, 12, pdrs_commit="pdrs-commit")
        assert object_identity.canonicalization_version == CANONICALIZATION_VERSION
        object_hash = ledger.record_object(object_identity, space.unrank(12))
        assert ledger.verify_object(space, object_hash) == "reconstructed"

        environment = environment_manifest(extra={"calendar": "TARGET", "evaluation_date": "2026-08-04"})
        oracle = {"name": "roundtrip", "tolerance": 0.0}
        parameters = {"worker": 0, "workers": 1}
        execution = build_execution_identity(
            object_hash,
            adapter_name="reference",
            adapter_version="2",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            external_data_snapshot="sha256:data",
            finspace_commit="finspace-commit",
        )
        execution_hash = ledger.record_execution(
            execution,
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            result={"ok": True},
        )
        assert ledger.verify_execution(
            execution_hash,
            adapter_name="reference",
            adapter_version="2",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            external_data_snapshot="sha256:data",
            observed_result={"ok": True},
        ) == "reproduced"
        assert ledger.verify_execution(
            execution_hash,
            adapter_name="reference",
            adapter_version="2",
            environment={**environment, "machine": "other"},
            oracle_config=oracle,
            execution_parameters=parameters,
            external_data_snapshot="sha256:data",
        ) == "environment-mismatch"
        assert ledger.verify_execution(
            execution_hash,
            adapter_name="reference",
            adapter_version="2",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            external_data_snapshot=None,
        ) == "external-data-unavailable"
        assert ledger.verify_execution(
            execution_hash,
            adapter_name="reference",
            adapter_version="2",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            external_data_snapshot="sha256:data",
            observed_result={"ok": False},
        ) == "result-divergence"
        exported = ledger.export_manifest(execution_hash)
        assert exported["ledger_schema_version"] == 2
        assert exported["object"]["rank"] == 12


def test_record_execution_rejects_hash_mismatch() -> None:
    space = FakeSpace()
    with (
        tempfile.TemporaryDirectory() as directory,
        ReplayLedger(Path(directory) / "ledger.sqlite") as ledger,
    ):
        object_hash = ledger.record_object(build_object_identity(space, 1), space.unrank(1))
        environment = {"python": "3.13"}
        oracle = {"oracle": "x"}
        parameters = {"x": 1}
        identity = build_execution_identity(
            object_hash,
            adapter_name="a",
            adapter_version="1",
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
        )
        bad = type(identity)(**{**identity.__dict__, "environment_hash": digest({"wrong": True})})
        try:
            ledger.record_execution(
                bad,
                environment=environment,
                oracle_config=oracle,
                execution_parameters=parameters,
            )
        except ValueError as error:
            assert "environment_hash" in str(error)
        else:
            raise AssertionError("mismatched environment hash was accepted")
