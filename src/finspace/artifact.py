"""Reproducible file manifests and deterministic ZIP archives."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactEntry:
    path: str
    sha256: str
    size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_manifest(root: str | Path, paths: list[str | Path]) -> tuple[ArtifactEntry, ...]:
    base = Path(root).resolve()
    entries: list[ArtifactEntry] = []
    for item in sorted((Path(path) for path in paths), key=lambda value: value.as_posix()):
        absolute = item if item.is_absolute() else base / item
        absolute = absolute.resolve()
        try:
            relative = absolute.relative_to(base)
        except ValueError as error:
            raise ValueError(f"artifact path {absolute} is outside root {base}") from error
        if not absolute.is_file():
            raise ValueError(f"artifact path is not a file: {relative}")
        entries.append(
            ArtifactEntry(
                path=relative.as_posix(),
                sha256=sha256_file(absolute),
                size=absolute.stat().st_size,
            )
        )
    return tuple(entries)


def write_manifest(path: str | Path, entries: tuple[ArtifactEntry, ...]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"manifest_version": "1", "files": [entry.to_dict() for entry in entries]}
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_sha256sums(path: str | Path, entries: tuple[ArtifactEntry, ...]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(f"{entry.sha256}  {entry.path}\n" for entry in entries),
        encoding="utf-8",
    )


def verify_artifact_manifest(root: str | Path, entries: tuple[ArtifactEntry, ...]) -> bool:
    base = Path(root)
    for entry in entries:
        candidate = base / entry.path
        if not candidate.is_file():
            return False
        if candidate.stat().st_size != entry.size:
            return False
        if sha256_file(candidate) != entry.sha256:
            return False
    return True


def build_reproducible_zip(
    root: str | Path,
    entries: tuple[ArtifactEntry, ...],
    output: str | Path,
) -> Path:
    """Create a deterministic ZIP from an already-hashed artifact manifest."""

    base = Path(root)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fixed_timestamp = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in sorted(entries, key=lambda item: item.path):
            info = zipfile.ZipInfo(entry.path, date_time=fixed_timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (base / entry.path).read_bytes())
    return target
