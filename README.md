# FinSpace

**Exact, rank-addressable financial scenario and protocol spaces.**

FinSpace compiles a finite financial schema into one exact integer domain. Every valid record receives one canonical rank, and every rank reconstructs one valid record under the matching schema and canonicalization version.

```text
financial record  <---- exact bijection ---->  integer in [0, N)
```

A rank can serve as a schema-relative object coordinate, cache key, checkpoint coordinate, deterministic worker assignment, duplicate-free sampling coordinate, or position in complete finite-domain enumeration. FinSpace is powered by [PDRS](https://github.com/abdullah-x-bd/PDRS).

## Research-software scope

FinSpace is not presented as a universal replacement for financial simulation, property-based testing, covering arrays, constraint solvers, or numerical libraries. Its narrower purpose is to make **bounded dependent financial domains exactly addressable and reproducibly executable**.

FinSpace 0.2 adds exact finite cross-field constraints, integer-weight sampling, mixed rank allocation, schema migration maps, failure shrinking, integrity-protected handles, campaign manifests, retry provenance, portable shard manifests, generic invalid-record mutations, and reproducible artifact packaging.

The repository maintains an explicit [claims and non-claims contract](docs/claims.md), a [formal model](docs/theory.md), a direct explanation of [what FinSpace contributes beyond PDRS](docs/pdrs-vs-finspace.md), and a [1-30 final completion audit](docs/final-audit.md).

The complete evidence suite tests:

- exact agreement with independent valid-object enumeration;
- compiler scaling against logical and Cartesian domain size;
- direct random access by rank;
- deterministic partition coverage and non-overlap;
- checkpoint interruption, resume, failure retry, and attempt provenance;
- object-versus-execution replay semantics;
- exact integer-weight selection behavior;
- contiguous, strided, and deterministic permuted allocation;
- schema-evolution preservation and rank churn;
- exact finite table constraints;
- canonical-rank failure shrinking;
- checksum and MAC rank-handle tamper detection;
- campaign manifest identity;
- generic invalid-record mutations;
- QuantLib scenario execution;
- FIX New Order Single generation;
- bounded pain.001 and pacs.008 XML generation;
- deliberately invalid finance and replay controls;
- evidence-file checksums and deterministic archive construction.

Reproduce the complete 1-30 evidence package with:

```bash
python -m experiments.final_reproduce --output evidence/generated
```

See [benchmark and evidence methodology](docs/benchmark-methodology.md).

## Why it exists

Financial testing and risk workflows often build a Cartesian product and filter invalid combinations afterward. This becomes expensive when valid choices depend on earlier fields, workers repeat costly calculations, campaigns must resume after interruption, and a failed object must be reconstructed precisely.

FinSpace compiles the valid bounded domain and addresses it directly:

```python
from finspace.templates import european_option_space

space = european_option_space()
worker = space.partition(worker_id=3, worker_count=32)

for rank in worker:
    scenario = space.unrank(rank)
    result = price(scenario)
    save(rank, result)
```

## Installation

```bash
pip install finspace
```

Optional integrations:

```bash
pip install "finspace[tabular]"
pip install "finspace[quantlib]"
pip install "finspace[fix]"
pip install "finspace[iso20022]"
pip install "finspace[all]"
```

For development:

```bash
git clone https://github.com/abdullah-x-bd/FinSpace.git
cd FinSpace
pip install -e ".[dev,all]"
```

## Basic example

```python
from finspace import Field, Schema, Space

schema = Schema(
    name="option-grid",
    fields=(
        Field.enum("option_type", ["call", "put"]),
        Field.enum("currency", ["USD", "EUR"]),
        Field.dependent(
            "rate",
            "currency",
            {
                "USD": [0.01, 0.03, 0.05],
                "EUR": [-0.01, 0.00, 0.02],
            },
        ),
        Field.enum("spot", [90.0, 100.0, 110.0]),
        Field.enum("strike", [90.0, 100.0, 110.0]),
        Field.enum("maturity_days", [30, 90, 365]),
    ),
)

space = Space(schema)
record = {
    "option_type": "call",
    "currency": "USD",
    "rate": 0.03,
    "spot": 100.0,
    "strike": 110.0,
    "maturity_days": 90,
}

rank = space.rank(record)
assert space.unrank(rank) == record
```

## Exact cross-field constraints

Use `TableConstraint` when admissibility depends on combinations of fields rather than one parent field alone:

```python
from finspace import Field, Schema, Space, TableConstraint

schema = Schema(
    name="currency-engine",
    fields=(
        Field.enum("currency", ["USD", "EUR", "JPY"]),
        Field.enum("engine", ["analytic", "fd", "tree"]),
    ),
    constraints=(
        TableConstraint(
            ("currency", "engine"),
            (
                ("USD", "analytic"),
                ("USD", "fd"),
                ("EUR", "analytic"),
                ("JPY", "tree"),
            ),
        ),
    ),
)

space = Space(schema)
assert space.count == 4
```

The compiler prunes partial assignments that cannot extend to an allowed row. This remains a finite table-relation mechanism, not a general SMT or arbitrary-predicate solver.

## Sampling and distributed allocation

```python
records = space.sample(100, replace=False, seed=7)
weighted = space.weighted_sampler([1] * space.count).sample(100, seed=7)
partitions = space.partitions(worker_count=8)
permuted = space.allocations(worker_count=8, strategy="permuted", seed=7)
```

`sample()` targets complete-object uniformity. Integer-weight sampling targets an explicitly supplied object distribution. `sample_stratified()` targets balance across a named unconditional field. Allocation strategies are deterministic and disjoint, although equal object counts do not guarantee equal execution cost.

The deterministic affine permutation used by `strategy="permuted"` is for reproducible workload mixing. It is not a cryptographic permutation.

## Schema evolution

Dense ranks are schema-relative. FinSpace does not claim arbitrary edits preserve rank numbers.

```python
from finspace import compare_spaces

migration = compare_spaces(old_space, new_space)
print(migration.rank_churn_fraction)
new_rank = migration.migrate_rank(old_rank)
```

The bounded migration tool compares canonical records, reports preserved, added, and removed objects, and exposes rank churn explicitly.

## Failure shrinking

```python
from finspace import shrink_failure

result = shrink_failure(
    space,
    failing_rank,
    lambda record: system_under_test(record).failed,
)
```

The default shrinker searches canonical rank order. If the full earlier prefix is examined it returns the smallest failing rank in that order. Canonical rank order is reproducible, but it is not claimed to equal domain-specific structural simplicity.

## Integrity-protected rank handles

A raw rank is compact and exactly addressable, but it has no intrinsic integrity protection. FinSpace 0.2 can wrap a rank and schema hash in a checksum or keyed MAC handle:

```python
from finspace import create_rank_handle, parse_rank_handle

handle = create_rank_handle(space, 42)
assert parse_rank_handle(handle.encode()).verify(space)

authenticated = create_rank_handle(space, 42, key=secret_key)
assert authenticated.verify(space, key=secret_key)
```

Checksum mode targets accidental corruption. MAC mode targets keyed authenticity. Neither makes the underlying rank confidential.

## Checkpointed execution and retries

```python
from finspace.runner import Runner
from finspace.adapters.quantlib import QuantLibEuropeanOptionPricer

runner = Runner(
    space,
    QuantLibEuropeanOptionPricer(),
    backend="thread",
    max_workers=8,
    checkpoint="option-results.sqlite",
    run_id="daily-risk",
    max_retries=2,
)
summary = runner.run(limit=50_000)
```

A checkpoint binds completed ranks to the schema and engine hashes and refuses to resume against an incompatible space. Attempt counts are persisted. Failed ranks remain distinct from completed ranks and remain eligible for later execution.

## Campaign and cluster manifests

`CampaignManifest` records the semantic execution inputs for one campaign. `ShardManifest` transports a deterministic worker allocation without requiring FinSpace itself to depend on Ray, Dask, Spark, Kubernetes, or a particular batch scheduler.

```python
from finspace import build_campaign_manifest, build_shard_manifests

campaign = build_campaign_manifest(
    space,
    selection={"strategy": "permuted"},
    seed=7,
    worker_count=16,
)
shards = build_shard_manifests(space, 16, strategy="permuted", seed=7)
```

These are scheduler-neutral integration surfaces. The repository does not claim every external cluster topology has been validated.

## Object reconstruction and execution reproduction

FinSpace separates two evidentiary levels.

An **object identity** binds:

```text
canonicalization version || schema hash || rank || PDRS version/commit
```

It reconstructs one canonical structured object under the matching schema.

An **execution identity** additionally binds:

```text
FinSpace version/commit
adapter name and version
environment manifest
oracle configuration
execution parameters
external-data snapshot
result digest
```

A schema hash and rank alone do not reproduce an execution result. FinSpace reports explicit states such as `adapter-mismatch`, `environment-mismatch`, `oracle-mismatch`, `external-data-unavailable`, and `result-divergence` instead of making a broad exact-replay claim.

See [Object reconstruction and execution reproduction](docs/replay.md).

## Finance integrations

FinSpace includes bounded integrations for:

- QuantLib scenario and pricing workflows;
- SimpleFIX financial-message generation;
- bounded ISO 20022 XML generation for pain.001 and pacs.008 workflows;
- NumPy, pandas, and Arrow output.

These adapters demonstrate orchestration. FinSpace does not make pricing formulas, numerical kernels, matrix operations, or Monte Carlo paths intrinsically faster. The included FIX and ISO 20022 profiles are bounded test profiles, not universal production conformance profiles.

## Reproducible artifact package

The final reproduction command emits raw JSON/CSV evidence, a human-readable summary, a SHA-256 manifest, `SHA256SUMS.txt`, and a deterministic `finspace-evidence.zip` archive.

```bash
python -m experiments.final_reproduce --output evidence/generated
```

This makes independent reproduction and permanent archival straightforward without pretending that self-reproduction is independent validation.

## CLI

```bash
finspace inspect examples/european_options.yaml
finspace sample examples/european_options.yaml -n 5 --seed 42
finspace rank examples/european_options.yaml scenario.json
finspace unrank examples/european_options.yaml 1234
finspace partition examples/european_options.yaml --workers 16 --worker 3
finspace export examples/european_options.yaml scenarios.jsonl --limit 1000
```

## Limitations

- Object-uniform sampling is not universally optimal for defect discovery or market realism.
- Object-level weighted sampling materializes weights and therefore has an explicit domain-size cap.
- Contiguous rank intervals do not guarantee balanced execution cost.
- A raw rank is not an integrity-protected identifier; use a protected rank handle where integrity matters.
- Arbitrary schema edits do not preserve ranks; migration maps report preservation and churn rather than hiding it.
- Canonical-rank shrinking is deterministic but not a universal structural shrink metric.
- Object reconstruction does not guarantee execution-result reproduction.
- Scheduler-neutral shard manifests do not establish validation of every external distributed runtime.
- FinSpace does not replace QuantLib, property-based testing, covering arrays, general constraint solvers, or stochastic simulation.
- Timing evidence is environment-specific and is not a universal performance guarantee.
- Independent adoption and external reproduction cannot be self-certified by this repository.

## Documentation

- [Quick start](docs/quickstart.md)
- [Claims and non-claims](docs/claims.md)
- [Formal model](docs/theory.md)
- [PDRS and FinSpace](docs/pdrs-vs-finspace.md)
- [Benchmark and evidence methodology](docs/benchmark-methodology.md)
- [Schema language](docs/schema-language.md)
- [Sampling and partitioning](docs/sampling-and-partitioning.md)
- [Checkpointed runner](docs/runner.md)
- [Object reconstruction and execution reproduction](docs/replay.md)
- [Finance adapters](docs/adapters.md)
- [Architecture](docs/architecture.md)
- [Limitations and safety](docs/limitations.md)
- [Final completion audit](docs/final-audit.md)
- [Evidence artifacts](evidence/README.md)
- [Release and deployment](docs/releasing.md)

## Status

FinSpace 0.2 is a beta research-software release candidate. Pin package versions, schema hashes, canonicalization versions, adapters, environments, oracle configurations, external-data snapshots, selection policy, and seeds for reproducible evaluation campaigns.
