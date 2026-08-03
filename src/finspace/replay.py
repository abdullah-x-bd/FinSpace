"""Versioned object and execution replay records for FinSpace."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
from typing import Any, Mapping, Protocol

CANONICALIZATION_VERSION = "2"
LEDGER_SCHEMA_VERSION = 2


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON for hashes and ledger payloads."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def package_version(name: str, fallback: str = "unknown") -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return fallback


class RankSpace(Protocol):
    schema_hash: str

    def unrank(self, rank: int) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class ObjectIdentity:
    canonicalization_version: str
    schema_hash: str
    rank: int
    pdrs_version: str
    pdrs_commit: str | None = None

    def validate(self) -> None:
        if not self.canonicalization_version:
            raise ValueError("canonicalization_version is required")
        if len(self.schema_hash) != 64 or any(ch not in "0123456789abcdef" for ch in self.schema_hash.lower()):
            raise ValueError("schema_hash must be a hexadecimal SHA-256 digest")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 0:
            raise ValueError("rank must be a non-negative integer")
        if not self.pdrs_version:
            raise ValueError("pdrs_version is required")

    @property
    def identity_hash(self) -> str:
        self.validate()
        return digest(asdict(self))


@dataclass(frozen=True)
class ExecutionIdentity:
    object_identity_hash: str
    finspace_version: str
    finspace_commit: str | None
    adapter_name: str
    adapter_version: str
    environment_hash: str
    oracle_config_hash: str
    external_data_snapshot: str | None
    execution_parameters_hash: str

    def validate(self) -> None:
        required = {
            "object_identity_hash": self.object_identity_hash,
            "finspace_version": self.finspace_version,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "environment_hash": self.environment_hash,
            "oracle_config_hash": self.oracle_config_hash,
            "execution_parameters_hash": self.execution_parameters_hash,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"execution identity is missing: {', '.join(missing)}")

    @property
    def identity_hash(self) -> str:
        self.validate()
        return digest(asdict(self))


def environment_manifest(*, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Capture execution-relevant environment facts without embedding secrets."""
    packages: dict[str, str] = {}
    for name in ("finspace", "pdrs", "QuantLib", "simplefix", "lxml", "xmlschema"):
        version = package_version(name)
        if version != "unknown":
            packages[name] = version
    selected_environment = {
        key: os.environ[key]
        for key in ("TZ", "LANG", "LC_ALL", "PYTHONHASHSEED")
        if key in os.environ
    }
    manifest: dict[str, Any] = {
        "manifest_version": "1",
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "byteorder": sys.byteorder,
        "timezone": selected_environment.get("TZ"),
        "locale": {
            "LANG": selected_environment.get("LANG"),
            "LC_ALL": selected_environment.get("LC_ALL"),
        },
        "selected_environment": selected_environment,
        "packages": packages,
    }
    if extra:
        manifest["extra"] = dict(extra)
    return manifest


class ReplayLedger:
    """SQLite ledger separating object identity from execution evidence."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> ReplayLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ledger_schema (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS object_identity (
                identity_hash TEXT PRIMARY KEY,
                canonicalization_version TEXT NOT NULL,
                schema_hash TEXT NOT NULL,
                rank INTEGER NOT NULL CHECK(rank >= 0),
                pdrs_version TEXT NOT NULL,
                pdrs_commit TEXT,
                canonical_object_json TEXT NOT NULL,
                canonical_object_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS execution_identity (
                identity_hash TEXT PRIMARY KEY,
                object_identity_hash TEXT NOT NULL REFERENCES object_identity(identity_hash),
                finspace_version TEXT NOT NULL,
                finspace_commit TEXT,
                adapter_name TEXT NOT NULL,
                adapter_version TEXT NOT NULL,
                environment_hash TEXT NOT NULL,
                environment_json TEXT NOT NULL,
                oracle_config_hash TEXT NOT NULL,
                oracle_config_json TEXT NOT NULL,
                external_data_snapshot TEXT,
                execution_parameters_hash TEXT NOT NULL,
                execution_parameters_json TEXT NOT NULL,
                result_hash TEXT,
                result_json TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS execution_object_idx
                ON execution_identity(object_identity_hash);
            """
        )
        current = self.connection.execute("SELECT MAX(version) FROM ledger_schema").fetchone()[0]
        if current is None:
            self.connection.execute(
                "INSERT INTO ledger_schema(version, applied_at) VALUES (?, ?)",
                (LEDGER_SCHEMA_VERSION, _utc_now()),
            )
        elif current > LEDGER_SCHEMA_VERSION:
            raise RuntimeError(f"ledger schema {current} is newer than supported {LEDGER_SCHEMA_VERSION}")
        self.connection.commit()

    def record_object(self, identity: ObjectIdentity, record: Mapping[str, Any]) -> str:
        identity.validate()
        object_json = canonical_json(record).decode("utf-8")
        object_hash = hashlib.sha256(object_json.encode("utf-8")).hexdigest()
        identity_hash = identity.identity_hash
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO object_identity(
                    identity_hash, canonicalization_version, schema_hash, rank,
                    pdrs_version, pdrs_commit, canonical_object_json,
                    canonical_object_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity_hash) DO UPDATE SET
                    canonical_object_json=excluded.canonical_object_json,
                    canonical_object_hash=excluded.canonical_object_hash
                """,
                (
                    identity_hash,
                    identity.canonicalization_version,
                    identity.schema_hash,
                    identity.rank,
                    identity.pdrs_version,
                    identity.pdrs_commit,
                    object_json,
                    object_hash,
                    _utc_now(),
                ),
            )
        return identity_hash

    def record_execution(
        self,
        identity: ExecutionIdentity,
        *,
        environment: Mapping[str, Any],
        oracle_config: Mapping[str, Any],
        execution_parameters: Mapping[str, Any],
        result: Any = None,
        status: str = "completed",
    ) -> str:
        identity.validate()
        environment_hash = digest(environment)
        oracle_hash = digest(oracle_config)
        parameters_hash = digest(execution_parameters)
        if environment_hash != identity.environment_hash:
            raise ValueError("environment_hash does not match the canonical manifest")
        if oracle_hash != identity.oracle_config_hash:
            raise ValueError("oracle_config_hash does not match the canonical configuration")
        if parameters_hash != identity.execution_parameters_hash:
            raise ValueError("execution_parameters_hash does not match the canonical parameters")
        result_json = None if result is None else canonical_json(result).decode("utf-8")
        result_hash = None if result_json is None else hashlib.sha256(result_json.encode("utf-8")).hexdigest()
        identity_hash = identity.identity_hash
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO execution_identity(
                    identity_hash, object_identity_hash, finspace_version, finspace_commit,
                    adapter_name, adapter_version, environment_hash, environment_json,
                    oracle_config_hash, oracle_config_json, external_data_snapshot,
                    execution_parameters_hash, execution_parameters_json,
                    result_hash, result_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity_hash,
                    identity.object_identity_hash,
                    identity.finspace_version,
                    identity.finspace_commit,
                    identity.adapter_name,
                    identity.adapter_version,
                    identity.environment_hash,
                    canonical_json(environment).decode("utf-8"),
                    identity.oracle_config_hash,
                    canonical_json(oracle_config).decode("utf-8"),
                    identity.external_data_snapshot,
                    identity.execution_parameters_hash,
                    canonical_json(execution_parameters).decode("utf-8"),
                    result_hash,
                    result_json,
                    status,
                    _utc_now(),
                ),
            )
        return identity_hash

    def get_object(self, identity_hash: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM object_identity WHERE identity_hash=?", (identity_hash,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown object identity {identity_hash}")
        return dict(row)

    def get_execution(self, identity_hash: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM execution_identity WHERE identity_hash=?", (identity_hash,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown execution identity {identity_hash}")
        return dict(row)

    def replay_object(self, space: RankSpace, identity_hash: str) -> Mapping[str, Any]:
        row = self.get_object(identity_hash)
        if row["canonicalization_version"] != CANONICALIZATION_VERSION:
            raise ValueError("canonicalization-version-mismatch")
        if row["schema_hash"] != space.schema_hash:
            raise ValueError("schema-mismatch")
        record = dict(space.unrank(int(row["rank"])))
        if hashlib.sha256(canonical_json(record)).hexdigest() != row["canonical_object_hash"]:
            raise ValueError("object-digest-mismatch")
        return record

    def verify_object(self, space: RankSpace, identity_hash: str) -> str:
        try:
            self.replay_object(space, identity_hash)
        except ValueError as error:
            return str(error)
        except KeyError:
            return "unknown-object"
        return "reconstructed"

    def verify_execution(
        self,
        identity_hash: str,
        *,
        adapter_name: str,
        adapter_version: str,
        environment: Mapping[str, Any],
        oracle_config: Mapping[str, Any],
        execution_parameters: Mapping[str, Any],
        external_data_snapshot: str | None,
        observed_result: Any | None = None,
    ) -> str:
        try:
            row = self.get_execution(identity_hash)
        except KeyError:
            return "unknown-execution"
        if row["adapter_name"] != adapter_name or row["adapter_version"] != adapter_version:
            return "adapter-mismatch"
        if row["environment_hash"] != digest(environment):
            return "environment-mismatch"
        if row["oracle_config_hash"] != digest(oracle_config):
            return "oracle-mismatch"
        if row["execution_parameters_hash"] != digest(execution_parameters):
            return "execution-parameters-mismatch"
        if row["external_data_snapshot"] != external_data_snapshot:
            return "external-data-unavailable"
        if observed_result is not None and row["result_hash"] != digest(observed_result):
            return "result-divergence"
        return "reproduced"

    def export_manifest(self, identity_hash: str) -> dict[str, Any]:
        execution = self.get_execution(identity_hash)
        object_row = self.get_object(execution["object_identity_hash"])
        return {
            "ledger_schema_version": LEDGER_SCHEMA_VERSION,
            "object": object_row,
            "execution": execution,
        }


def build_object_identity(
    space: RankSpace,
    rank: int,
    *,
    pdrs_commit: str | None = None,
) -> ObjectIdentity:
    return ObjectIdentity(
        canonicalization_version=CANONICALIZATION_VERSION,
        schema_hash=space.schema_hash,
        rank=rank,
        pdrs_version=package_version("pdrs", "source"),
        pdrs_commit=pdrs_commit,
    )


def build_execution_identity(
    object_identity_hash: str,
    *,
    adapter_name: str,
    adapter_version: str,
    environment: Mapping[str, Any],
    oracle_config: Mapping[str, Any],
    execution_parameters: Mapping[str, Any],
    external_data_snapshot: str | None = None,
    finspace_commit: str | None = None,
) -> ExecutionIdentity:
    return ExecutionIdentity(
        object_identity_hash=object_identity_hash,
        finspace_version=package_version("finspace", "source"),
        finspace_commit=finspace_commit,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        environment_hash=digest(environment),
        oracle_config_hash=digest(oracle_config),
        external_data_snapshot=external_data_snapshot,
        execution_parameters_hash=digest(execution_parameters),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
