# FinSpace claims and non-claims

FinSpace is research software for exact, rank-addressable orchestration of bounded dependent financial domains. This document is the claim contract for the repository. Benchmarks and case studies should be interpreted against these statements rather than against broader claims about financial simulation or numerical computing.

## Core claims

### C1. Exact finite-domain representation

For one fixed FinSpace schema and canonicalization version, FinSpace compiles the valid bounded domain into a rank-addressable space. Every valid record has one integer rank in `[0, N)`, and every rank reconstructs one valid record.

The correctness obligation is therefore two-sided:

- `unrank(rank(record)) == record` for every valid canonical record;
- `rank(unrank(i)) == i` for every integer `i` in `[0, N)`.

### C2. Dependency-aware construction

FinSpace represents conditional and dependency-driven fields without requiring callers to construct the complete Cartesian product and discard invalid combinations. The compiler memoizes equivalent suffix states according to the prior context that can influence the remaining fields.

This is a representation and orchestration claim. It is not a claim that FinSpace always has lower constant overhead than a hand-written generator on small domains.

### C3. Deterministic coordinates

Ranks are deterministic coordinates inside one exact schema. They can be used for direct object reconstruction, duplicate-free sampling, deterministic partitioning, checkpoint coordinates, and failure reproduction.

Ranks are schema-relative. They are not globally stable identifiers and are not cryptographic identifiers.

### C4. Exact worker partitioning

For a fixed space and worker count, the built-in contiguous rank partitions are deterministic, disjoint, and collectively cover `[0, N)`. Object counts differ by at most one between workers.

This does not imply equal execution cost when individual scenarios have heterogeneous runtimes.

### C5. Checkpointable execution

FinSpace can checkpoint completed ranks and resume a compatible campaign without intentionally re-running ranks already recorded as completed. Failed ranks remain eligible for retry.

The SQLite backend is a local checkpoint mechanism, not a multi-host coordination database.

### C6. Object reconstruction and execution reproduction are different evidentiary levels

An object identity binds the canonicalization version, schema hash, rank, and PDRS version information. It is sufficient to reconstruct the canonical object when the corresponding schema is retained.

An execution identity additionally binds FinSpace and adapter versions, environment information, oracle configuration, execution parameters, an external-data snapshot identifier, and the result digest. FinSpace reports mismatch states rather than treating object reconstruction as proof of full execution reproduction.

### C7. Finance-specific orchestration

FinSpace adds a finance-facing schema layer, scenario templates, checkpointed execution, replay semantics, and bounded adapters for QuantLib, FIX message generation, and ISO 20022 message generation. These capabilities are tested as separate finance case studies in the evidence suite.

## Explicit non-claims

FinSpace does **not** claim that:

1. object-uniform sampling is a model of market probability or historical likelihood;
2. equal-rank partitions provide equal runtime or risk importance;
3. QuantLib pricing formulas, matrix operations, Monte Carlo arithmetic, FIX encoders, or XML libraries become intrinsically faster because FinSpace is used;
4. a rank remains stable after arbitrary schema edits, field reordering, value reordering, or canonicalization changes;
5. ranks provide confidentiality, authenticity, or tamper resistance;
6. exact object reconstruction guarantees exact execution-result reproduction;
7. FinSpace replaces property-based testing, covering arrays, stochastic simulation, Monte Carlo methods, or domain-specific risk models;
8. the included FIX and ISO 20022 profiles constitute universal production conformance profiles;
9. the included ISO 20022 builder proves conformance to every external network, bank, or scheme-specific XSD/profile;
10. FinSpace always outperforms a recursive generator or Cartesian iterator on small domains.

## Evidence standard

A repository-level claim is considered supported only when the evidence suite contains a reproducible test or experiment that exercises the public FinSpace API and records the corresponding result. Documentation examples alone are not evidence.

The canonical evidence entry point is:

```bash
python -m experiments.reproduce --output evidence/generated
```

The evidence suite intentionally records negative results and cases where simpler baselines are competitive.