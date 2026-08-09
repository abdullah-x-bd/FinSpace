"""One-command reproduction for the complete FinSpace 0.2 evidence package."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finspace.artifact import (
    build_artifact_manifest,
    build_reproducible_zip,
    verify_artifact_manifest,
    write_manifest,
    write_sha256sums,
)

from .final_hardening import final_hardening_evidence
from .reproduce import reproduce


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def reproduce_all(output: Path, *, quick: bool = False) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    original = reproduce(output, quick=quick)
    final = final_hardening_evidence()
    _write_json(output / "final_hardening.json", final)
    if not final["passed"]:
        raise AssertionError("one or more FinSpace 0.2 final-hardening checks failed")

    data_paths = sorted(
        path.relative_to(output)
        for path in output.rglob("*")
        if path.is_file() and path.name not in {"MANIFEST.json", "SHA256SUMS.txt", "finspace-evidence.zip"}
    )
    data_entries = build_artifact_manifest(output, data_paths)
    write_manifest(output / "MANIFEST.json", data_entries)
    write_sha256sums(output / "SHA256SUMS.txt", data_entries)
    if not verify_artifact_manifest(output, data_entries):
        raise AssertionError("generated evidence does not match its artifact manifest")

    archive_paths = data_paths + [Path("MANIFEST.json"), Path("SHA256SUMS.txt")]
    archive_entries = build_artifact_manifest(output, archive_paths)
    archive = build_reproducible_zip(output, archive_entries, output / "finspace-evidence.zip")
    result = {
        "original_evidence_passed": all(
            original[name]["passed"]
            for name in (
                "checkpoint_recovery",
                "replay_matrix",
                "quantlib",
                "fix",
                "iso20022",
                "negative_controls",
            )
        ),
        "final_hardening_passed": bool(final["passed"]),
        "manifest_files": len(data_entries),
        "archive": archive.name,
        "passed": True,
    }
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce the complete FinSpace 0.2 evidence package")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/generated"),
        help="directory for generated evidence and reproducible archive",
    )
    parser.add_argument("--quick", action="store_true", help="use the smaller benchmark profile")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = reproduce_all(args.output, quick=args.quick)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
