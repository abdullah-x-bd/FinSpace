# Object reconstruction and execution reproduction

FinSpace records two related identities.

## Object identity

An object identity contains the canonicalization version, schema hash, rank, PDRS version, and optional PDRS commit. It reconstructs one canonical structured object within the matching schema and canonicalization version.

## Execution identity

An execution identity also binds the FinSpace and adapter versions, canonical environment manifest, oracle configuration, execution parameters, external-data snapshot, and result digest. FinSpace reports explicit mismatch states instead of describing object reconstruction as execution reproduction.

Possible verification outcomes include:

- `reproduced`
- `adapter-mismatch`
- `environment-mismatch`
- `oracle-mismatch`
- `execution-parameters-mismatch`
- `external-data-unavailable`
- `result-divergence`

The environment manifest deliberately excludes secrets. Users must supply stable identifiers for market data, calendars, evaluation dates, model files, and other external inputs that affect results.
