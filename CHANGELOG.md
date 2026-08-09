# Changelog

## 0.2.0

FinSpace 0.2.0 completes the repository's research-hardening programme while preserving the central rule that dense ranks are schema-relative coordinates, not universal identifiers.

### Added

- Exact integer-weight sampling with exact rational probability reporting.
- Contiguous, strided, and deterministic permuted rank allocation.
- Exact bounded schema migration maps with rank-churn reporting.
- Finite cross-field table constraints compiled with exact pruning.
- Deterministic canonical-rank shrinking for reproducible failures.
- Checksum-protected and HMAC-authenticated rank handles.
- Versioned campaign manifests with semantic and full-manifest digests.
- Execution retries with attempt provenance in checkpoints.
- Failed-rank and checkpoint-status introspection.
- Cluster-neutral shard manifests for external schedulers.
- Generic deterministic invalid-record mutation generation.
- A complete second-stage evidence campaign.
- SHA-256 artifact manifests and deterministic evidence ZIP creation.

### Changed

- Development status advances from Alpha to Beta.
- Public package version advances from 0.1.0 to 0.2.0.
- Table constraints participate in schema hashing and compilation identity.
- Checkpoints retain execution-attempt counts and migrate older task tables in place.
- CI type-checks the complete semantic core and runs the complete 1-30 evidence package.

### Explicit limits

- Weighted object-level sampling materializes one weight per object and has an explicit safety cap.
- Deterministic affine rank permutation is for reproducible workload mixing, not cryptography.
- Schema migration maps preserve canonical records where possible; they do not make ranks stable across arbitrary edits.
- Canonical-rank shrinking is reproducible but is not a universal structural simplicity metric.
- Cluster-neutral shard manifests are scheduler integration surfaces, not evidence that every Ray, Dask, or Spark deployment topology has been validated.
- Checksum handles detect accidental corruption; keyed MAC handles provide authenticity when keys are managed correctly.
- External independent reproduction, adoption evidence, and permanent DOI archiving require actors and services outside this repository.

## 0.1.0

- Declarative finite field schema language.
- Conditional and dependency-driven values.
- Exact rank, unrank, validation, and schema identity.
- Sampling with and without replacement.
- Field-stratified sampling.
- Exact worker partitions.
- NumPy, pandas, and Arrow conversion.
- SQLite checkpointed runner.
- QuantLib, SimpleFIX, and ISO 20022 adapters.
- CLI, examples, tests, documentation, and CI.
