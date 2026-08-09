# FinSpace evidence

This directory is the canonical location for machine-generated evidence from the FinSpace research-software validation suite.

Do not hand-edit generated measurements.

## Reproduce

Full evidence run:

```bash
python -m experiments.reproduce --output evidence/generated
```

Smaller pull-request profile:

```bash
python -m experiments.reproduce --output evidence/generated --quick
```

Or use:

```bash
make evidence
make evidence-quick
```

## Generated files

A successful run writes:

- `generated/results.json`, the complete machine-readable result bundle;
- `generated/scalability.csv`, compiler/domain scaling measurements;
- `generated/baselines.csv`, Cartesian, recursive, and FinSpace enumeration comparisons;
- `generated/random_access.csv`, direct-addressability comparisons;
- `generated/partitions.csv`, deterministic worker-allocation checks;
- `generated/SUMMARY.md`, a human-readable pass/fail summary.

## Evidence scope

The suite supports the repository claims defined in `docs/claims.md`. It tests:

1. compilation of dependent finite domains without materializing complete objects;
2. exact agreement with independent enumeration baselines;
3. direct rank-addressed access;
4. deterministic worker coverage and non-overlap;
5. checkpoint interruption and resume;
6. explicit replay mismatch states;
7. QuantLib scenario execution;
8. FIX message generation;
9. ISO 20022 message generation and XML well-formedness;
10. negative controls that must fail.

## Timing results

Timing results are specific to the execution environment. They are evidence about the measured run, not universal performance guarantees. The benchmark methodology deliberately includes strong streaming baselines and permits negative results.

See `docs/benchmark-methodology.md` for the complete protocol.
