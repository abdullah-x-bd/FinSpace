from __future__ import annotations

import argparse
import csv
import gc
import itertools
import json
import math
import platform
import statistics
import tempfile
import time
import tracemalloc
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from finspace import Field, RecordValidationError, Schema, Space
from finspace.adapters import (
    ISO20022PaymentBuilder,
    QuantLibEuropeanOptionPricer,
    SimpleFixNewOrderSingleEncoder,
)
from finspace.replay import (
    ReplayLedger,
    build_execution_identity,
    build_object_identity,
    environment_manifest,
)
from finspace.runner import CheckpointStore, Runner
from finspace.templates import european_option_space, fix_order_space, iso20022_payment_space


@dataclass(frozen=True)
class Profile:
    size: int
    currencies: tuple[str, ...]
    all_rates: tuple[float, ...]
    rates_by_currency: dict[str, tuple[float, ...]]
    spots: tuple[float, ...]
    strikes: tuple[float, ...]
    maturities: tuple[int, ...]

    @property
    def cartesian_candidates(self) -> int:
        return (
            len(self.currencies)
            * len(self.all_rates)
            * len(self.spots)
            * len(self.strikes)
            * len(self.maturities)
        )


def profile(size: int) -> Profile:
    currencies = tuple(f"C{i:02d}" for i in range(size))
    all_rates = tuple(round(-0.02 + 0.005 * i, 6) for i in range(size))
    rates_by_currency = {
        currency: all_rates[: 1 + index % size] for index, currency in enumerate(currencies)
    }
    spots = tuple(float(80 + i) for i in range(size * 2))
    strikes = tuple(float(80 + i) for i in range(size * 2))
    maturities = (7, 30, 90, 365)
    return Profile(
        size=size,
        currencies=currencies,
        all_rates=all_rates,
        rates_by_currency=rates_by_currency,
        spots=spots,
        strikes=strikes,
        maturities=maturities,
    )


def schema_for_profile(item: Profile) -> Schema:
    return Schema(
        name=f"evidence-profile-{item.size}",
        version="1",
        fields=(
            Field.enum("currency", item.currencies),
            Field.dependent("rate", "currency", item.rates_by_currency),
            Field.enum("spot", item.spots),
            Field.enum("strike", item.strikes),
            Field.enum("maturity_days", item.maturities),
        ),
        metadata={"evidence_profile_size": item.size},
    )


def measure(function: Callable[[], Any]) -> tuple[Any, float, int]:
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    value = function()
    seconds = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, seconds, peak_bytes


def cartesian_count(item: Profile) -> int:
    valid = 0
    for currency, rate, spot, strike, maturity in itertools.product(
        item.currencies,
        item.all_rates,
        item.spots,
        item.strikes,
        item.maturities,
    ):
        _ = (spot, strike, maturity)
        if rate in item.rates_by_currency[currency]:
            valid += 1
    return valid


def recursive_count(item: Profile) -> int:
    valid = 0
    for currency in item.currencies:
        for rate in item.rates_by_currency[currency]:
            for spot in item.spots:
                for strike in item.strikes:
                    for maturity in item.maturities:
                        _ = (rate, spot, strike, maturity)
                        valid += 1
    return valid


def cartesian_nth(item: Profile, target: int) -> dict[str, Any]:
    current = -1
    for currency, rate, spot, strike, maturity in itertools.product(
        item.currencies,
        item.all_rates,
        item.spots,
        item.strikes,
        item.maturities,
    ):
        if rate not in item.rates_by_currency[currency]:
            continue
        current += 1
        if current == target:
            return {
                "currency": currency,
                "rate": rate,
                "spot": spot,
                "strike": strike,
                "maturity_days": maturity,
            }
    raise IndexError(target)


def recursive_nth(item: Profile, target: int) -> dict[str, Any]:
    current = -1
    for currency in item.currencies:
        for rate in item.rates_by_currency[currency]:
            for spot in item.spots:
                for strike in item.strikes:
                    for maturity in item.maturities:
                        current += 1
                        if current == target:
                            return {
                                "currency": currency,
                                "rate": rate,
                                "spot": spot,
                                "strike": strike,
                                "maturity_days": maturity,
                            }
    raise IndexError(target)


def benchmark_scalability(*, quick: bool) -> list[dict[str, Any]]:
    sizes = (2, 4, 8, 12) if quick else (2, 4, 8, 12, 16, 24, 32)
    rows: list[dict[str, Any]] = []
    for size in sizes:
        item = profile(size)
        space, seconds, peak_bytes = measure(lambda item=item: Space(schema_for_profile(item)))
        rows.append(
            {
                "size": size,
                "logical_objects": space.count,
                "cartesian_candidates": item.cartesian_candidates,
                "compiled_states": space.compilation.states,
                "compile_seconds": seconds,
                "compile_peak_bytes": peak_bytes,
                "valid_fraction_of_cartesian": space.count / item.cartesian_candidates,
            }
        )
    return rows


def benchmark_baselines(*, quick: bool) -> list[dict[str, Any]]:
    sizes = (2, 4) if quick else (2, 4, 6, 8)
    rows: list[dict[str, Any]] = []
    for size in sizes:
        item = profile(size)
        space = Space(schema_for_profile(item))
        implementations: tuple[tuple[str, Callable[[], int]], ...] = (
            ("cartesian_filter", lambda item=item: cartesian_count(item)),
            ("recursive_generator", lambda item=item: recursive_count(item)),
            (
                "finspace_enumerate",
                lambda space=space: sum(1 for _ in space.enumerate()),
            ),
        )
        for name, function in implementations:
            count, seconds, peak_bytes = measure(function)
            if count != space.count:
                raise AssertionError(f"{name} produced {count}, expected {space.count}")
            rows.append(
                {
                    "size": size,
                    "implementation": name,
                    "valid_objects": count,
                    "cartesian_candidates": item.cartesian_candidates,
                    "seconds": seconds,
                    "peak_bytes": peak_bytes,
                }
            )
    return rows


def benchmark_random_access(*, quick: bool) -> list[dict[str, Any]]:
    item = profile(6 if quick else 8)
    space = Space(schema_for_profile(item))
    targets = (0, space.count // 2, space.count - 1)
    rows: list[dict[str, Any]] = []
    for target in targets:
        expected = space.unrank(target)
        for name, function in (
            ("cartesian_filter", lambda target=target: cartesian_nth(item, target)),
            ("recursive_generator", lambda target=target: recursive_nth(item, target)),
            ("finspace_unrank", lambda target=target: space.unrank(target)),
        ):
            repetitions = 1 if name != "finspace_unrank" else 100
            values: list[float] = []
            observed = None
            for _ in range(repetitions):
                started = time.perf_counter()
                observed = function()
                values.append(time.perf_counter() - started)
            if observed != expected:
                raise AssertionError(f"{name} returned a different record for rank {target}")
            rows.append(
                {
                    "rank": target,
                    "implementation": name,
                    "repetitions": repetitions,
                    "median_seconds": statistics.median(values),
                    "min_seconds": min(values),
                }
            )
    return rows


def partition_evidence(*, quick: bool) -> list[dict[str, Any]]:
    space = Space(schema_for_profile(profile(8 if quick else 12)))
    worker_counts = (1, 2, 3, 7, 16) if quick else (1, 2, 3, 7, 16, 32, 64, 128)
    rows: list[dict[str, Any]] = []
    for worker_count in worker_counts:
        partitions = space.partitions(worker_count)
        sizes = [len(partition) for partition in partitions]
        adjacent = all(left.stop == right.start for left, right in itertools.pairwise(partitions))
        complete = (
            partitions[0].start == 0
            and partitions[-1].stop == space.count
            and sum(sizes) == space.count
        )
        rows.append(
            {
                "worker_count": worker_count,
                "logical_objects": space.count,
                "complete": complete,
                "adjacent": adjacent,
                "min_objects": min(sizes),
                "max_objects": max(sizes),
                "max_imbalance": max(sizes) - min(sizes),
            }
        )
        if not complete or not adjacent or max(sizes) - min(sizes) > 1:
            raise AssertionError(f"partition invariant failed for {worker_count} workers")
    return rows


def checkpoint_recovery_evidence() -> dict[str, Any]:
    space = Space(
        Schema(
            name="checkpoint-evidence",
            fields=(Field.enum("value", tuple(range(200))),),
        )
    )

    def calculate(record: dict[str, Any]) -> dict[str, int]:
        value = int(record["value"])
        return {"value": value, "square": value * value}

    with tempfile.TemporaryDirectory() as directory:
        checkpoint = Path(directory) / "checkpoint.sqlite"
        first = Runner(space, calculate, checkpoint=checkpoint, run_id="recovery").run(
            ranks=range(80)
        )
        second = Runner(space, calculate, checkpoint=checkpoint, run_id="recovery").run(
            ranks=range(space.count)
        )
        with CheckpointStore(checkpoint) as store:
            completed = list(store.results("recovery", "completed"))

    observed = {item.rank: item.result for item in completed}
    reference = {rank: {"value": rank, "square": rank * rank} for rank in range(space.count)}
    return {
        "logical_objects": space.count,
        "first_run": first.to_dict(),
        "resume_run": second.to_dict(),
        "recorded_completed": len(completed),
        "duplicate_ranks": len(completed) - len(observed),
        "missing_ranks": sorted(set(reference) - set(observed)),
        "result_divergences": sum(
            observed.get(rank) != result for rank, result in reference.items()
        ),
        "passed": observed == reference
        and first.completed == 80
        and second.skipped == 80
        and second.completed == 120,
    }


def replay_matrix_evidence() -> dict[str, Any]:
    space = Space(
        Schema(
            name="replay-evidence",
            fields=(Field.enum("case", ("base", "stress")), Field.enum("value", (1, 2, 3))),
        )
    )
    environment = environment_manifest(
        extra={"calendar": "NullCalendar", "evaluation_date": "2026-08-02"}
    )
    oracle = {"name": "reference", "tolerance": 0.0}
    parameters = {"worker": 0, "workers": 1}
    result = {"npv": 12.5, "currency": "USD"}

    with tempfile.TemporaryDirectory() as directory:
        ledger_path = Path(directory) / "replay.sqlite"
        with ReplayLedger(ledger_path) as ledger:
            object_identity = build_object_identity(space, 2, pdrs_commit="evidence")
            object_hash = ledger.record_object(object_identity, space.unrank(2))
            execution_identity = build_execution_identity(
                object_hash,
                adapter_name="reference",
                adapter_version="1",
                environment=environment,
                oracle_config=oracle,
                execution_parameters=parameters,
                external_data_snapshot="sha256:market-data-v1",
                finspace_commit="evidence",
            )
            execution_hash = ledger.record_execution(
                execution_identity,
                environment=environment,
                oracle_config=oracle,
                execution_parameters=parameters,
                result=result,
            )

            cases = {
                "reproduced": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="1",
                    environment=environment,
                    oracle_config=oracle,
                    execution_parameters=parameters,
                    external_data_snapshot="sha256:market-data-v1",
                    observed_result=result,
                ),
                "adapter_mismatch": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="2",
                    environment=environment,
                    oracle_config=oracle,
                    execution_parameters=parameters,
                    external_data_snapshot="sha256:market-data-v1",
                ),
                "environment_mismatch": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="1",
                    environment={**environment, "machine": "different"},
                    oracle_config=oracle,
                    execution_parameters=parameters,
                    external_data_snapshot="sha256:market-data-v1",
                ),
                "oracle_mismatch": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="1",
                    environment=environment,
                    oracle_config={"name": "reference", "tolerance": 1e-6},
                    execution_parameters=parameters,
                    external_data_snapshot="sha256:market-data-v1",
                ),
                "parameters_mismatch": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="1",
                    environment=environment,
                    oracle_config=oracle,
                    execution_parameters={"worker": 1, "workers": 2},
                    external_data_snapshot="sha256:market-data-v1",
                ),
                "external_data_unavailable": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="1",
                    environment=environment,
                    oracle_config=oracle,
                    execution_parameters=parameters,
                    external_data_snapshot=None,
                ),
                "result_divergence": ledger.verify_execution(
                    execution_hash,
                    adapter_name="reference",
                    adapter_version="1",
                    environment=environment,
                    oracle_config=oracle,
                    execution_parameters=parameters,
                    external_data_snapshot="sha256:market-data-v1",
                    observed_result={"npv": 12.6, "currency": "USD"},
                ),
            }
            object_status = ledger.verify_object(space, object_hash)

    expected = {
        "reproduced": "reproduced",
        "adapter_mismatch": "adapter-mismatch",
        "environment_mismatch": "environment-mismatch",
        "oracle_mismatch": "oracle-mismatch",
        "parameters_mismatch": "execution-parameters-mismatch",
        "external_data_unavailable": "external-data-unavailable",
        "result_divergence": "result-divergence",
    }
    return {
        "object_status": object_status,
        "cases": cases,
        "expected": expected,
        "passed": object_status == "reconstructed" and cases == expected,
    }


def quantlib_case_study() -> dict[str, Any]:
    space = european_option_space(
        currencies=("USD", "EUR"),
        spots=(90.0, 100.0, 110.0),
        strikes=(90.0, 100.0, 110.0),
        maturities_days=(30, 90),
        volatilities=(0.1, 0.2),
        dividends=(0.0,),
        rates_by_currency={"USD": (0.01, 0.03), "EUR": (0.0, 0.02)},
    )
    pricer = QuantLibEuropeanOptionPricer(
        binomial_steps=101,
        fd_time_steps=40,
        fd_grid_points=40,
    )
    ranks = sorted(
        {
            0,
            1,
            2,
            space.count // 3,
            space.count // 3 + 1,
            space.count // 3 + 2,
            space.count // 2,
            space.count - 3,
            space.count - 2,
            space.count - 1,
        }
    )
    rows: list[dict[str, Any]] = []
    for rank in ranks:
        record = space.unrank(rank)
        result = pricer(record)
        numeric = [result["npv"], result["delta"], result["gamma"], result["vega"]]
        if not all(value is None or math.isfinite(float(value)) for value in numeric):
            raise AssertionError(f"non-finite QuantLib result for rank {rank}")
        rows.append(
            {
                "rank": rank,
                "engine": record["engine"],
                "currency": record["currency"],
                "npv": result["npv"],
                "delta": result["delta"],
                "gamma": result["gamma"],
                "vega": result["vega"],
            }
        )
    return {
        "domain_count": space.count,
        "executed": len(rows),
        "engines_seen": sorted({str(row["engine"]) for row in rows}),
        "results": rows,
        "passed": bool(rows),
    }


def fix_case_study(*, quick: bool) -> dict[str, Any]:
    space = fix_order_space()
    encoder = SimpleFixNewOrderSingleEncoder()
    limit = min(space.count, 30 if quick else 100)
    lengths: list[int] = []
    types: set[str] = set()
    for rank in range(limit):
        record = space.unrank(rank)
        payload = encoder(record)
        if b"35=D\x01" not in payload or not payload.endswith(b"\x01"):
            raise AssertionError(f"invalid FIX encoding for rank {rank}")
        lengths.append(len(payload))
        types.add(str(record["order_type"]))
    return {
        "domain_count": space.count,
        "executed": limit,
        "order_types_seen": sorted(types),
        "min_bytes": min(lengths),
        "max_bytes": max(lengths),
        "passed": len(lengths) == limit,
    }


def iso20022_case_study(*, quick: bool) -> dict[str, Any]:
    space = iso20022_payment_space()
    builder = ISO20022PaymentBuilder()
    per_message = 10 if quick else 30
    selected: dict[str, list[int]] = {"pain.001.001.13": [], "pacs.008.001.14": []}
    for rank in range(space.count):
        message = str(space.unrank(rank)["message"])
        if len(selected[message]) < per_message:
            selected[message].append(rank)
        if all(len(ranks) == per_message for ranks in selected.values()):
            break
    ranks = selected["pain.001.001.13"] + selected["pacs.008.001.14"]
    namespaces: set[str] = set()
    messages: set[str] = set()
    lengths: list[int] = []
    for rank in ranks:
        record = space.unrank(rank)
        payload = builder(record)
        root = ElementTree.fromstring(payload)
        if not root.tag.endswith("Document"):
            raise AssertionError(f"unexpected ISO 20022 root for rank {rank}")
        if root.tag.startswith("{"):
            namespaces.add(root.tag[1:].split("}", 1)[0])
        messages.add(str(record["message"]))
        lengths.append(len(payload))
    return {
        "domain_count": space.count,
        "executed": len(ranks),
        "messages_seen": sorted(messages),
        "namespaces_seen": sorted(namespaces),
        "min_bytes": min(lengths),
        "max_bytes": max(lengths),
        "scope_note": "This case study establishes deterministic bounded generation and XML well-formedness, not universal scheme-specific XSD conformance.",
        "passed": len(messages) == 2 and len(lengths) == len(ranks),
    }


def negative_controls() -> dict[str, Any]:
    outcomes: dict[str, bool] = {}

    fix_space = fix_order_space()
    market = next(record for record in fix_space.enumerate() if record["order_type"] == "1")
    invalid_market = {**market, "price": 100.0}
    try:
        fix_space.rank(invalid_market)
    except RecordValidationError:
        outcomes["fix_inactive_price_rejected"] = True
    else:
        outcomes["fix_inactive_price_rejected"] = False

    iso_space = iso20022_payment_space()
    pain = next(
        record for record in iso_space.enumerate() if record["message"] == "pain.001.001.13"
    )
    invalid_pain = {**pain, "priority": "HIGH"}
    try:
        iso_space.rank(invalid_pain)
    except RecordValidationError:
        outcomes["iso_inactive_priority_rejected"] = True
    else:
        outcomes["iso_inactive_priority_rejected"] = False

    try:
        ISO20022PaymentBuilder()({"message": "unsupported"})
    except ValueError:
        outcomes["unsupported_iso_message_rejected"] = True
    else:
        outcomes["unsupported_iso_message_rejected"] = False

    option = european_option_space(
        currencies=("USD",),
        spots=(100.0,),
        strikes=(100.0,),
        maturities_days=(30,),
        volatilities=(0.2,),
        dividends=(0.0,),
        rates_by_currency={"USD": (0.03,)},
    ).unrank(0)
    option["engine"] = "unsupported"
    try:
        QuantLibEuropeanOptionPricer()(option)
    except ValueError:
        outcomes["unsupported_quantlib_engine_rejected"] = True
    else:
        outcomes["unsupported_quantlib_engine_rejected"] = False

    conditioned = fix_space.condition(order_type="2")
    outcomes["conditioned_fix_records_are_parent_valid"] = all(
        fix_space.unrank(fix_space.rank(record)) == record for record in conditioned.enumerate()
    )
    return {"outcomes": outcomes, "passed": all(outcomes.values())}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_summary(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# FinSpace evidence summary",
        "",
        "This file is generated by `python -m experiments.reproduce`.",
        "",
        "## Environment",
        "",
        f"- Python: `{platform.python_version()}`",
        f"- Platform: `{platform.platform()}`",
        "",
        "## Experiment status",
        "",
    ]
    for name in (
        "checkpoint_recovery",
        "replay_matrix",
        "quantlib",
        "fix",
        "iso20022",
        "negative_controls",
    ):
        status = results[name].get("passed", False)
        lines.append(f"- {name}: **{'PASS' if status else 'FAIL'}**")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Timing numbers are environment-specific and should be interpreted comparatively within the same run. The evidence suite does not claim universal constant-factor speedups. It tests exactness, direct addressability, deterministic partitioning, recovery semantics, replay mismatch detection, and bounded finance integrations.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def reproduce(output: Path, *, quick: bool) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    scalability = benchmark_scalability(quick=quick)
    baselines = benchmark_baselines(quick=quick)
    random_access = benchmark_random_access(quick=quick)
    partitions = partition_evidence(quick=quick)
    results: dict[str, Any] = {
        "metadata": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "quick": quick,
        },
        "scalability": scalability,
        "baselines": baselines,
        "random_access": random_access,
        "partitions": partitions,
        "checkpoint_recovery": checkpoint_recovery_evidence(),
        "replay_matrix": replay_matrix_evidence(),
        "quantlib": quantlib_case_study(),
        "fix": fix_case_study(quick=quick),
        "iso20022": iso20022_case_study(quick=quick),
        "negative_controls": negative_controls(),
    }
    write_json(output / "results.json", results)
    write_csv(output / "scalability.csv", scalability)
    write_csv(output / "baselines.csv", baselines)
    write_csv(output / "random_access.csv", random_access)
    write_csv(output / "partitions.csv", partitions)
    write_summary(output / "SUMMARY.md", results)

    required = (
        results["checkpoint_recovery"]["passed"],
        results["replay_matrix"]["passed"],
        results["quantlib"]["passed"],
        results["fix"]["passed"],
        results["iso20022"]["passed"],
        results["negative_controls"]["passed"],
    )
    if not all(required):
        raise AssertionError("one or more FinSpace evidence checks failed")
    return results


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproduce FinSpace research-software evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/generated"),
        help="directory for generated evidence",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run the smaller pull-request evidence profile",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    reproduce(args.output, quick=args.quick)
    print(f"FinSpace evidence written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
