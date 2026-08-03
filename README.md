# FinSpace

**Exact, rank-addressable financial scenario and protocol spaces.**

FinSpace compiles a finite financial schema into one exact integer domain. Every valid record receives one canonical rank, and every rank reconstructs one valid record under the matching schema and canonicalization version.

```text
financial record  <---- exact bijection ---->  integer in [0, N)
```

A rank can serve as a schema-relative object identifier, cache key, checkpoint coordinate, deterministic worker assignment, duplicate-free sampling coordinate, or position in complete finite-domain enumeration. FinSpace is powered by [PDRS](https://github.com/abdullah-x-bd/PDRS).

## Why it exists

Financial testing and risk workflows often build a Cartesian product and filter invalid combinations afterward. This becomes expensive when valid choices depend on earlier fields, workers repeat costly calculations, campaigns must resume after interruption, and a failed object must be reconstructed precisely.

FinSpace compiles only the valid finite domain and addresses it directly:

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

## Sampling and distributed allocation

```python
records = space.sample(10_000, replace=False, seed=7)
stratified = space.sample_stratified("option_type", 1_000, seed=7)
partitions = space.partitions(worker_count=8)
```

`sample()` targets complete-object uniformity. `sample_stratified()` targets balance across a named field. Deterministic partitions are disjoint and cover the domain exactly, although equal object counts do not guarantee equal execution cost.

## Checkpointed execution

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
)
summary = runner.run(partition=space.partition(0, 4), limit=50_000)
```

A checkpoint binds completed ranks to the schema hash and refuses to resume against a different schema.

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

The versioned SQLite replay ledger and CLI support:

```bash
finspace replay-object LEDGER SCHEMA OBJECT_ID
finspace verify-object LEDGER SCHEMA OBJECT_ID
finspace replay-execution LEDGER EXECUTION_ID \
  --adapter-name quantlib --adapter-version 1.43 \
  --oracle oracle.json --parameters parameters.json
finspace verify-environment LEDGER EXECUTION_ID
finspace export-manifest LEDGER EXECUTION_ID manifest.json
```

See [Object reconstruction and execution reproduction](docs/replay.md).

## Finance integrations

FinSpace includes bounded integrations for:

- QuantLib scenario and pricing workflows
- SimpleFIX financial-message generation
- ISO 20022 XML generation and validation
- NumPy, pandas, and Arrow output

These adapters demonstrate orchestration. FinSpace does not make pricing formulas, numerical kernels, matrix operations, or Monte Carlo paths intrinsically faster.

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

- Object-uniform sampling is not universally optimal for defect discovery.
- Contiguous rank intervals do not guarantee balanced execution cost.
- A rank is not an integrity-protected identifier.
- Arbitrary schema edits do not preserve ranks.
- Object reconstruction does not guarantee execution-result reproduction.
- FinSpace does not replace QuantLib, property-based testing, covering arrays, or stochastic simulation.

## Documentation

- [Quick start](docs/quickstart.md)
- [Schema language](docs/schema-language.md)
- [Sampling and partitioning](docs/sampling-and-partitioning.md)
- [Checkpointed runner](docs/runner.md)
- [Object reconstruction and execution reproduction](docs/replay.md)
- [Finance adapters](docs/adapters.md)
- [Architecture](docs/architecture.md)
- [Limitations and safety](docs/limitations.md)
- [Release and deployment](docs/releasing.md)

## Status

FinSpace 0.1 is an alpha release. Pin package versions, schema hashes, canonicalization versions, adapters, environments, oracle configurations, and external-data snapshots for reproducible evaluation campaigns.
