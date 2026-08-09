"""Versioned campaign manifests for reproducible FinSpace executions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .replay import canonical_json, digest, environment_manifest, package_version
from .space import Space


@dataclass(frozen=True)
class CampaignManifest:
    manifest_version: str
    schema_hash: str
    engine_hash: str
    object_count: int
    finspace_version: str
    pdrs_version: str
    selection: Mapping[str, Any]
    seed: int | str | None
    worker_count: int
    adapter_name: str
    adapter_version: str
    oracle_config: Mapping[str, Any]
    environment: Mapping[str, Any]
    external_data_snapshot: str | None
    created_at: str
    extra: Mapping[str, Any]

    @property
    def semantic_digest(self) -> str:
        payload = asdict(self)
        payload.pop("created_at")
        return digest(payload)

    @property
    def manifest_digest(self) -> str:
        return digest(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["semantic_digest"] = self.semantic_digest
        result["manifest_digest"] = self.manifest_digest
        return result

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_json(self.to_dict()) + b"\n")

    @classmethod
    def load(cls, path: str | Path) -> CampaignManifest:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("campaign manifest must be a JSON object")
        raw.pop("semantic_digest", None)
        raw.pop("manifest_digest", None)
        return cls(**raw)

    def validate_space(self, space: Space) -> bool:
        return (
            self.schema_hash == space.schema_hash
            and self.engine_hash == space.engine_hash
            and self.object_count == space.count
        )


def build_campaign_manifest(
    space: Space,
    *,
    selection: Mapping[str, Any],
    seed: int | str | None = None,
    worker_count: int = 1,
    adapter_name: str = "python-callable",
    adapter_version: str = "1",
    oracle_config: Mapping[str, Any] | None = None,
    external_data_snapshot: str | None = None,
    environment_extra: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> CampaignManifest:
    if worker_count <= 0:
        raise ValueError("worker_count must be positive")
    if not adapter_name or not adapter_version:
        raise ValueError("adapter name and version are required")
    return CampaignManifest(
        manifest_version="1",
        schema_hash=space.schema_hash,
        engine_hash=space.engine_hash,
        object_count=space.count,
        finspace_version=package_version("finspace", "source"),
        pdrs_version=package_version("pdrs", "source"),
        selection=dict(selection),
        seed=seed,
        worker_count=worker_count,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        oracle_config=dict(oracle_config or {}),
        environment=environment_manifest(extra=environment_extra),
        external_data_snapshot=external_data_snapshot,
        created_at=datetime.now(UTC).isoformat(),
        extra=dict(extra or {}),
    )
