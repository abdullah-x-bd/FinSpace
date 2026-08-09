from __future__ import annotations

from dataclasses import replace

import pytest

from finspace import Field, Schema, Space
from finspace.artifact import (
    build_artifact_manifest,
    build_reproducible_zip,
    verify_artifact_manifest,
    write_manifest,
    write_sha256sums,
)
from finspace.campaign import CampaignManifest, build_campaign_manifest


def _space() -> Space:
    return Space(Schema(name="campaign", fields=(Field.enum("x", (1, 2, 3)),)))


def test_campaign_manifest_roundtrip_and_semantic_digest(tmp_path) -> None:
    space = _space()
    manifest = build_campaign_manifest(
        space,
        selection={"strategy": "permuted"},
        seed=42,
        worker_count=3,
        adapter_name="reference",
        adapter_version="2",
        oracle_config={"tolerance": 1e-8},
        external_data_snapshot="sha256:data",
    )
    assert manifest.validate_space(space)
    later = replace(manifest, created_at="2099-01-01T00:00:00+00:00")
    assert later.semantic_digest == manifest.semantic_digest
    assert later.manifest_digest != manifest.manifest_digest
    path = tmp_path / "campaign.json"
    manifest.save(path)
    loaded = CampaignManifest.load(path)
    assert loaded == manifest
    assert loaded.validate_space(space)


def test_campaign_manifest_rejects_invalid_worker_count() -> None:
    with pytest.raises(ValueError, match="worker_count"):
        build_campaign_manifest(_space(), selection={}, worker_count=0)


def test_artifact_manifest_detects_tamper_and_zip_is_reproducible(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("alpha\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta\n", encoding="utf-8")
    entries = build_artifact_manifest(tmp_path, ["a.txt", "b.txt"])
    assert verify_artifact_manifest(tmp_path, entries)
    write_manifest(tmp_path / "MANIFEST.json", entries)
    write_sha256sums(tmp_path / "SHA256SUMS.txt", entries)
    first = build_reproducible_zip(tmp_path, entries, tmp_path / "first.zip")
    second = build_reproducible_zip(tmp_path, entries, tmp_path / "second.zip")
    assert first.read_bytes() == second.read_bytes()
    (tmp_path / "a.txt").write_text("changed\n", encoding="utf-8")
    assert not verify_artifact_manifest(tmp_path, entries)


def test_artifact_manifest_rejects_paths_outside_root(tmp_path) -> None:
    outside = tmp_path.parent / "outside-finspace.txt"
    outside.write_text("nope", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="outside root"):
            build_artifact_manifest(tmp_path, [outside])
    finally:
        outside.unlink(missing_ok=True)
