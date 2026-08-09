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

### C4. Exact worker allocation

For a fixed space and worker count, the built-in contiguous, strided, and deterministic permuted allocation strategies are disjoint and collectively cover `[0, N)`. The first and permuted interval strategies differ in object count by at most one between workers; strided allocation has the same count-balance property.

This does not imply equal execution cost when individual scenarios have heterogeneous runtimes. The affine permutation is a reproducible mixing mechanism, not a cryptographic permutation.

### C5. Checkpointable and retryable execution

FinSpace can checkpoint completed ranks and resume a compatible campaign without intentionally re-running ranks already recorded as completed. Failed ranks remain eligible for retry. Retry attempts are recorded and exposed through checkpoint introspection.

The SQLite backend is a local checkpoint mechanism, not a multi-host coordination database.

### C6. Object reconstruction and execution reproduction are different evidentiary levels

An object identity binds the canonicalization version, schema hash, rank, and PDRS version information. It is sufficient to reconstruct the canonical object when the corresponding schema is retained.

An execution identity additionally binds FinSpace and adapter versions, environment information, oracle configuration, execution parameters, an external-data snapshot identifier, and the result digest. FinSpace reports mismatch states rather than treating object reconstruction as proof of full execution reproduction.

### C7. Finance-specific orchestration

FinSpace adds a finance-facing schema layer, scenario templates, checkpointed execution, replay semantics, and bounded adapters for QuantLib, FIX message generation, and ISO 20022 message generation. These capabilities are tested as separate finance case studies in the evidence suite.

### C8. Exact finite cross-field table constraints

A `TableConstraint` declares an exact finite relation over two or more schema fields. The compiler prunes a partial assignment when no declared row can extend it and admits a complete record only when the constrained tuple is allowed. Table constraints participate in schema identity.

This is a finite relation mechanism. It is not a claim that FinSpace is a general constraint, SAT, SMT, or symbolic-program solver.

### C9. Exact integer-weight selection

For a bounded space and a vector of non-negative integer weights, FinSpace performs replacement draws using exact integer tickets and exposes the corresponding probabilities as exact rational values. Without-replacement selection uses sequential probability-proportional-to-size draws over the remaining positive weights.

Object-level weighting materializes one weight per object and therefore has an explicit size cap when weights are derived by evaluating a function across the domain.

### C10. Schema evolution is explicit rather than rank-stable

FinSpace can compare two bounded schema versions by canonical record equality and construct an exact migration map for objects that survive the change. It reports added objects, removed objects, stable ranks, and rank churn.

This does not make dense ranks stable under arbitrary schema edits. The map is the compatibility artifact.

### C11. Failure shrinking is deterministic under canonical rank order

Given a known failing rank and a failure predicate, the baseline shrinker searches earlier canonical ranks within an explicit evaluation budget. If the full prefix is searched, it returns the globally earliest failing rank under that fixed schema's canonical order.

Canonical rank order is not claimed to be a universal metric of semantic or structural simplicity.

### C12. Integrity can be layered over rank coordinates

A protected rank handle binds the handle version, schema hash, and rank. Checksum mode detects accidental corruption according to the implemented digest; MAC mode verifies keyed authenticity according to the implemented HMAC construction.

The underlying dense rank remains neither confidential nor intrinsically authenticated. Key generation, storage, rotation, and access control remain deployment responsibilities.

### C13. Campaigns and shards are portable metadata

Campaign manifests bind selection policy, seed, worker count, adapter/oracle configuration, environment information, and external-data snapshot identifiers to a space. Shard manifests bind a worker to an exact deterministic rank allocation.

These artifacts are intentionally scheduler-neutral. Their existence does not establish that every Ray, Dask, Spark, Kubernetes, or batch-scheduler topology has been tested.

### C14. Evidence artifacts are hash-verifiable and reproducibly packaged

The final reproduction command writes a SHA-256 file manifest and constructs a deterministic ZIP from a sorted file set with normalized timestamps and permissions. Re-running under the same source and evidence outputs therefore provides a directly comparable artifact package.

This is artifact reproducibility, not independent scientific validation.

## Explicit non-claims

FinSpace does **not** claim that:

1. object-uniform or weighted sampling is automatically a model of market probability or historical likelihood;
2. equal object counts across rank allocations provide equal runtime, memory, risk importance, or defect-finding value;
3. QuantLib pricing formulas, matrix operations, Monte Carlo arithmetic, FIX encoders, or XML libraries become intrinsically faster because FinSpace is used;
4. a raw rank remains stable after arbitrary schema edits, field reordering, value reordering, constraint edits, or canonicalization changes;
5. a raw rank provides confidentiality, authenticity, or tamper resistance;
6. checksum mode provides cryptographic authenticity or confidentiality;
7. exact object reconstruction guarantees exact execution-result reproduction;
8. FinSpace replaces property-based testing, covering arrays, stochastic simulation, Monte Carlo methods, general constraint solvers, or domain-specific risk models;
9. the included FIX and ISO 20022 profiles constitute universal production conformance profiles;
10. the included ISO 20022 builder proves conformance to every external network, bank, or scheme-specific XSD/profile;
11. FinSpace always outperforms a recursive generator or Cartesian iterator on small domains;
12. canonical-rank shrinking always produces the semantically simplest failing case;
13. cluster-neutral manifests prove correctness of every external scheduler integration;
14. self-reproduction of the repository constitutes independent reproduction, external adoption, or confirmation of real-world defect discovery.

## Evidence standard

A repository-level empirical claim is considered supported only when the evidence suite contains a reproducible test or experiment that exercises the public FinSpace API and records the corresponding result. Documentation examples alone are not evidence.

The canonical FinSpace 0.2 evidence entry point is:

```bash
python -m experiments.final_reproduce --output evidence/generated
```

The evidence suite intentionally records negative results and cases where simpler baselines are competitive. The final completion boundary is documented in `docs/final-audit.md`.
