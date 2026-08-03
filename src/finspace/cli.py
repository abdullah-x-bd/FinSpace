"""Command-line interface for FinSpace."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .replay import ReplayLedger, digest, environment_manifest
from .space import Space


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


def _load_record(value: str) -> dict[str, Any]:
    candidate = Path(value)
    raw = json.loads(candidate.read_text(encoding="utf-8")) if candidate.exists() else json.loads(value)
    if not isinstance(raw, dict):
        raise ValueError("record must be a JSON object")
    return raw


def _load_mapping(path: str | None, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if path is None:
        return dict(default or {})
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _space(path: str) -> Space:
    return Space.load(path)


def command_inspect(args: argparse.Namespace) -> int:
    print(_json(_space(args.schema).describe()))
    return 0


def command_rank(args: argparse.Namespace) -> int:
    space = _space(args.schema)
    record = _load_record(args.record)
    print(_json(space.explain(record)))
    return 0


def command_unrank(args: argparse.Namespace) -> int:
    space = _space(args.schema)
    print(_json({"rank": args.rank, "record": space.unrank(args.rank)}))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    space = _space(args.schema)
    record = _load_record(args.record)
    rank = space.rank(record)
    print(_json({"valid": True, "rank": rank, "schema_hash": space.schema_hash}))
    return 0


def command_sample(args: argparse.Namespace) -> int:
    space = _space(args.schema)
    if args.stratify:
        sampled = space.sample_stratified(args.stratify, args.count, seed=args.seed, with_ranks=True)
    else:
        sampled = space.sample(args.count, replace=args.replace, seed=args.seed, with_ranks=True)
    for rank, record in sampled:
        print(json.dumps({"rank": rank, "record": record}, ensure_ascii=False, default=str))
    return 0


def command_partition(args: argparse.Namespace) -> int:
    space = _space(args.schema)
    partition = space.partition(args.worker, args.workers)
    print(_json(partition.to_dict()))
    return 0


def _rows(space: Space, start: int, stop: int) -> Iterable[dict[str, Any]]:
    for rank in range(start, stop):
        yield {"rank": rank, **space.unrank(rank)}


def command_export(args: argparse.Namespace) -> int:
    space = _space(args.schema)
    start = args.start
    stop = space.count if args.stop is None else args.stop
    if args.limit is not None:
        stop = min(stop, start + args.limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = _rows(space, start, stop)
    if args.format == "jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    else:
        first = next(iter(rows), None)
        with output.open("w", newline="", encoding="utf-8") as handle:
            if first is not None:
                writer = csv.DictWriter(handle, fieldnames=list(first))
                writer.writeheader()
                writer.writerow(first)
                for row in _rows(space, start + 1, stop):
                    writer.writerow(row)
    print(_json({"output": str(output), "start": start, "stop": stop, "count": stop - start}))
    return 0


def command_replay_object(args: argparse.Namespace) -> int:
    with ReplayLedger(args.ledger) as ledger:
        record = ledger.replay_object(_space(args.schema), args.object_id)
    print(_json({"status": "reconstructed", "object_id": args.object_id, "record": record}))
    return 0


def command_verify_object(args: argparse.Namespace) -> int:
    with ReplayLedger(args.ledger) as ledger:
        status = ledger.verify_object(_space(args.schema), args.object_id)
    print(_json({"status": status, "object_id": args.object_id}))
    return 0 if status == "reconstructed" else 1


def command_verify_environment(args: argparse.Namespace) -> int:
    manifest = environment_manifest(extra=_load_mapping(args.extra) if args.extra else None)
    with ReplayLedger(args.ledger) as ledger:
        execution = ledger.get_execution(args.execution_id)
    status = "matched" if execution["environment_hash"] == digest(manifest) else "environment-mismatch"
    print(_json({"status": status, "manifest": manifest, "execution_id": args.execution_id}))
    return 0 if status == "matched" else 1


def command_replay_execution(args: argparse.Namespace) -> int:
    environment = _load_mapping(args.environment, default=environment_manifest())
    oracle = _load_mapping(args.oracle)
    parameters = _load_mapping(args.parameters)
    observed = None if args.result is None else json.loads(Path(args.result).read_text(encoding="utf-8"))
    with ReplayLedger(args.ledger) as ledger:
        status = ledger.verify_execution(
            args.execution_id,
            adapter_name=args.adapter_name,
            adapter_version=args.adapter_version,
            environment=environment,
            oracle_config=oracle,
            execution_parameters=parameters,
            external_data_snapshot=args.external_data_snapshot,
            observed_result=observed,
        )
    print(_json({"status": status, "execution_id": args.execution_id}))
    return 0 if status == "reproduced" else 1


def command_export_manifest(args: argparse.Namespace) -> int:
    with ReplayLedger(args.ledger) as ledger:
        manifest = ledger.export_manifest(args.execution_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_json(manifest) + "\n", encoding="utf-8")
    print(_json({"status": "exported", "output": str(output), "execution_id": args.execution_id}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finspace",
        description="Compile and operate exact finite financial scenario spaces.",
    )
    parser.add_argument("--version", action="version", version="finspace 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser("inspect", help="show domain size, hashes, and fields")
    inspect.add_argument("schema")
    inspect.set_defaults(function=command_inspect)

    rank = subparsers.add_parser("rank", help="rank a JSON record")
    rank.add_argument("schema")
    rank.add_argument("record", help="JSON string or path to a JSON file")
    rank.set_defaults(function=command_rank)

    unrank = subparsers.add_parser("unrank", help="decode one integer rank")
    unrank.add_argument("schema")
    unrank.add_argument("rank", type=int)
    unrank.set_defaults(function=command_unrank)

    validate = subparsers.add_parser("validate", help="validate and rank a record")
    validate.add_argument("schema")
    validate.add_argument("record")
    validate.set_defaults(function=command_validate)

    sample = subparsers.add_parser("sample", help="sample valid records")
    sample.add_argument("schema")
    sample.add_argument("-n", "--count", type=int, default=1)
    sample.add_argument("--seed", default=None)
    sample.add_argument("--replace", action="store_true")
    sample.add_argument("--stratify", help="balance samples across an unconditional field")
    sample.set_defaults(function=command_sample)

    partition = subparsers.add_parser("partition", help="show one deterministic worker interval")
    partition.add_argument("schema")
    partition.add_argument("--workers", type=int, required=True)
    partition.add_argument("--worker", type=int, required=True)
    partition.set_defaults(function=command_partition)

    export = subparsers.add_parser("export", help="export an interval to JSONL or CSV")
    export.add_argument("schema")
    export.add_argument("output")
    export.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    export.add_argument("--start", type=int, default=0)
    export.add_argument("--stop", type=int)
    export.add_argument("--limit", type=int)
    export.set_defaults(function=command_export)

    replay_object = subparsers.add_parser("replay-object", help="reconstruct a recorded object")
    replay_object.add_argument("ledger")
    replay_object.add_argument("schema")
    replay_object.add_argument("object_id")
    replay_object.set_defaults(function=command_replay_object)

    verify_object = subparsers.add_parser("verify-object", help="verify a recorded object against a schema")
    verify_object.add_argument("ledger")
    verify_object.add_argument("schema")
    verify_object.add_argument("object_id")
    verify_object.set_defaults(function=command_verify_object)

    replay_execution = subparsers.add_parser("replay-execution", help="verify execution evidence and an optional observed result")
    replay_execution.add_argument("ledger")
    replay_execution.add_argument("execution_id")
    replay_execution.add_argument("--adapter-name", required=True)
    replay_execution.add_argument("--adapter-version", required=True)
    replay_execution.add_argument("--environment")
    replay_execution.add_argument("--oracle", required=True)
    replay_execution.add_argument("--parameters", required=True)
    replay_execution.add_argument("--external-data-snapshot")
    replay_execution.add_argument("--result")
    replay_execution.set_defaults(function=command_replay_execution)

    verify_environment = subparsers.add_parser("verify-environment", help="compare the current environment with a recorded execution")
    verify_environment.add_argument("ledger")
    verify_environment.add_argument("execution_id")
    verify_environment.add_argument("--extra")
    verify_environment.set_defaults(function=command_verify_environment)

    export_manifest = subparsers.add_parser("export-manifest", help="export object and execution evidence")
    export_manifest.add_argument("ledger")
    export_manifest.add_argument("execution_id")
    export_manifest.add_argument("output")
    export_manifest.set_defaults(function=command_export_manifest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.function(args))
    except Exception as error:
        parser.exit(2, f"finspace: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
