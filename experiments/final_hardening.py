"""Evidence for the FinSpace 0.2 final hardening tranche."""

from __future__ import annotations

import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from finspace import Field, Schema, Space, TableConstraint
from finspace.allocation import allocations
from finspace.campaign import build_campaign_manifest
from finspace.evolution import compare_spaces
from finspace.identity import create_rank_handle, parse_rank_handle
from finspace.mutations import invalid_mutations
from finspace.runner import CheckpointStore, Runner
from finspace.shrink import shrink_failure
from finspace.templates import fix_order_space
from finspace.weighted import WeightedSampler


def weighted_evidence() -> dict[str, Any]:
    space = Space(Schema(name="weighted-evidence", fields=(Field.enum("bucket", ("A", "B", "C")),)))
    sampler = WeightedSampler(space, (1, 3, 6))
    draws = sampler.sample(20_000, seed=20260809, with_ranks=True)
    counts = Counter(rank for rank, _ in draws)
    expected = [float(value) for value in sampler.probabilities()]
    empirical = [counts[index] / len(draws) for index in range(space.count)]
    unique = sampler.sample(3, replace=False, seed=20260809, with_ranks=True)
    return {
        "weights": list(sampler.weights),
        "exact_probabilities": [str(value) for value in sampler.probabilities()],
        "empirical_probabilities": empirical,
        "absolute_errors": [abs(left - right) for left, right in zip(empirical, expected, strict=True)],
        "no_replacement_ranks": [rank for rank, _ in unique],
        "passed": len({rank for rank, _ in unique}) == 3 and sampler.total_weight == 10,
    }


def allocation_evidence() -> dict[str, Any]:
    count = 120
    worker_count = 6
    schema_hash = "0" * 64
    branch = [0] * 60 + [1] * 40 + [2] * 20
    cost = [10 if value == 0 else 3 if value == 1 else 1 for value in branch]
    rows: dict[str, Any] = {}
    for strategy in ("contiguous", "strided", "permuted"):
        shards = allocations(schema_hash, count, worker_count, strategy=strategy, seed=20260809)
        observed = [rank for shard in shards for rank in shard]
        worker_costs = [sum(cost[rank] for rank in shard) for shard in shards]
        worker_branches = [
            {str(key): value for key, value in Counter(branch[rank] for rank in shard).items()}
            for shard in shards
        ]
        rows[strategy] = {
            "coverage_complete": sorted(observed) == list(range(count)),
            "duplicate_ranks": len(observed) - len(set(observed)),
            "worker_sizes": [len(shard) for shard in shards],
            "worker_costs": worker_costs,
            "max_cost_imbalance": max(worker_costs) - min(worker_costs),
            "worker_branch_counts": worker_branches,
        }
    return {
        "synthetic_cost_note": "Costs are deliberately heterogeneous to test allocation behavior; they are not finance runtime measurements.",
        "strategies": rows,
        "passed": all(
            row["coverage_complete"] and row["duplicate_ranks"] == 0 for row in rows.values()
        ),
    }


def evolution_evidence() -> dict[str, Any]:
    base = Space(Schema(name="evolution", version="1", fields=(Field.enum("x", ("a", "b", "c")),)))
    append = Space(
        Schema(name="evolution", version="2", fields=(Field.enum("x", ("a", "b", "c", "d")),))
    )
    reorder = Space(
        Schema(name="evolution", version="3", fields=(Field.enum("x", ("c", "a", "b")),))
    )
    appended = compare_spaces(base, append)
    reordered = compare_spaces(base, reorder)
    return {
        "append_only": appended.to_dict(),
        "reordered": reordered.to_dict(),
        "passed": appended.preserved == 3
        and appended.rank_churn == 0
        and reordered.preserved == 3
        and reordered.rank_churn == 3,
    }


def constraint_evidence() -> dict[str, Any]:
    allowed = (("USD", "analytic"), ("USD", "fd"), ("EUR", "analytic"), ("JPY", "tree"))
    space = Space(
        Schema(
            name="constraint-evidence",
            fields=(
                Field.enum("currency", ("USD", "EUR", "JPY")),
                Field.enum("engine", ("analytic", "fd", "tree")),
            ),
            constraints=(TableConstraint(("currency", "engine"), allowed),),
        )
    )
    observed = [tuple(record[field] for field in ("currency", "engine")) for record in space.enumerate()]
    return {
        "cartesian_candidates": 9,
        "valid_objects": space.count,
        "compiled_states": space.compilation.states,
        "records": observed,
        "passed": set(observed) == set(allowed) and space.count == len(allowed),
    }


def retry_evidence() -> dict[str, Any]:
    space = Space(Schema(name="retry-evidence", fields=(Field.enum("x", tuple(range(20))),)))
    calls: defaultdict[int, int] = defaultdict(int)

    def transient(record: dict[str, Any]) -> int:
        value = int(record["x"])
        calls[value] += 1
        if calls[value] == 1:
            raise RuntimeError("synthetic transient failure")
        return value * value

    with tempfile.TemporaryDirectory() as directory:
        checkpoint = Path(directory) / "retry.sqlite"
        summary = Runner(
            space,
            transient,
            checkpoint=checkpoint,
            run_id="retry-evidence",
            max_retries=1,
        ).run()
        with CheckpointStore(checkpoint) as store:
            attempts = [item.attempts for item in store.results("retry-evidence")]
            failed = sorted(store.failed_ranks("retry-evidence"))
    return {
        "summary": summary.to_dict(),
        "attempts": attempts,
        "failed_ranks": failed,
        "passed": summary.completed == space.count
        and summary.failed == 0
        and summary.retries == space.count
        and set(attempts) == {2},
    }


def integrity_evidence() -> dict[str, Any]:
    space = Space(Schema(name="integrity-evidence", fields=(Field.enum("x", tuple(range(50))),)))
    checksum = create_rank_handle(space, 17)
    parsed = parse_rank_handle(checksum.encode())
    tampered = parse_rank_handle(checksum.encode().replace(".17.", ".18."))
    authenticated = create_rank_handle(space, 17, key=b"finspace-evidence-key")
    return {
        "checksum_verified": parsed.verify(space),
        "tampered_rank_rejected": not tampered.verify(space),
        "mac_verified": authenticated.verify(space, key=b"finspace-evidence-key"),
        "wrong_mac_key_rejected": not authenticated.verify(space, key=b"wrong"),
        "scope_note": "Checksum mode detects accidental corruption. MAC mode provides keyed authenticity. Dense ranks alone provide neither property.",
        "passed": parsed.verify(space)
        and not tampered.verify(space)
        and authenticated.verify(space, key=b"finspace-evidence-key")
        and not authenticated.verify(space, key=b"wrong"),
    }


def shrinking_evidence() -> dict[str, Any]:
    space = Space(Schema(name="shrink-evidence", fields=(Field.enum("value", tuple(range(100))),)))
    result = shrink_failure(space, 91, lambda record: int(record["value"]) >= 23)
    return {
        **result.to_dict(),
        "shrunk_record": space.unrank(result.shrunk_rank),
        "scope_note": "This is canonical-rank shrinking, not a claim that rank order equals domain-specific structural simplicity.",
        "passed": result.shrunk_rank == 23 and result.complete_search,
    }


def mutation_evidence() -> dict[str, Any]:
    space = fix_order_space()
    record = next(item for item in space.enumerate() if item["order_type"] == "1")
    mutations = invalid_mutations(space, record)
    accepted: list[str] = []
    rejected: list[str] = []
    for mutation in mutations:
        try:
            space.rank(mutation.record)
        except Exception:
            rejected.append(mutation.label)
        else:
            accepted.append(mutation.label)
    return {
        "generated": len(mutations),
        "rejected": rejected,
        "accepted": accepted,
        "passed": bool(mutations) and not accepted,
    }


def campaign_evidence() -> dict[str, Any]:
    space = Space(Schema(name="campaign-evidence", fields=(Field.enum("x", tuple(range(10))),)))
    first = build_campaign_manifest(
        space,
        selection={"strategy": "permuted"},
        seed=123,
        worker_count=4,
        adapter_name="reference",
        adapter_version="1",
        oracle_config={"tolerance": 0.0},
        external_data_snapshot="sha256:synthetic-v1",
    )
    return {
        "semantic_digest": first.semantic_digest,
        "manifest_digest": first.manifest_digest,
        "validates_space": first.validate_space(space),
        "selection": dict(first.selection),
        "passed": first.validate_space(space) and first.semantic_digest != first.manifest_digest,
    }


def final_hardening_evidence() -> dict[str, Any]:
    results = {
        "weighted_sampling": weighted_evidence(),
        "allocation": allocation_evidence(),
        "schema_evolution": evolution_evidence(),
        "table_constraints": constraint_evidence(),
        "retry_recovery": retry_evidence(),
        "rank_integrity": integrity_evidence(),
        "shrinking": shrinking_evidence(),
        "invalid_mutations": mutation_evidence(),
        "campaign_manifest": campaign_evidence(),
    }
    results["passed"] = all(value["passed"] for value in results.values())
    return results
