# Benchmark and evidence methodology

The FinSpace evidence suite is designed to test repository claims rather than to maximize headline benchmark numbers.

Run the complete suite with:

```bash
python -m experiments.reproduce --output evidence/generated
```

Use the smaller pull-request profile with:

```bash
python -m experiments.reproduce --output evidence/generated --quick
```

## 1. Synthetic dependency profiles

Scalability and baseline experiments use deterministic finite schemas with:

- a root `currency` field;
- a `rate` field whose valid values depend on currency;
- independent spot, strike, and maturity fields.

The dependency map is deliberately asymmetric. Currency `C00` receives one valid rate, `C01` receives two, and so on. A Cartesian generator therefore encounters invalid `(currency, rate)` combinations, while a dependency-aware generator traverses only valid rates.

The experiments record both the Cartesian candidate count and the exact FinSpace valid-object count.

## 2. Compilation scaling

For increasing profile sizes the suite measures:

- logical valid-object count;
- raw Cartesian candidate count;
- compiled FinSpace/PDRS state count;
- compilation wall-clock time;
- peak Python allocation measured by `tracemalloc`.

The experiment does not enumerate the large logical spaces. Its purpose is to test whether exact addressability can be constructed without materializing every complete object.

Timing is environment-specific. The durable result is the relationship among logical cardinality, Cartesian cardinality, and compiled state count.

## 3. Enumeration baselines

Three implementations enumerate the same valid records:

1. `cartesian_filter`, using `itertools.product` followed by dependency filtering;
2. `recursive_generator`, using direct dependency-aware nested loops;
3. `finspace_enumerate`, using the public FinSpace API.

All methods are streaming rather than deliberately materializing giant lists. This makes the baseline harder and more honest. FinSpace is not expected to beat a simple hand-written recursive generator in every small case.

Each implementation must return exactly `space.count` valid objects or the experiment fails.

## 4. Random-access comparison

For the first, middle, and final valid object in a bounded domain, the suite compares:

- scanning a Cartesian-filter generator until the target;
- scanning a recursive valid-object generator until the target;
- `Space.unrank(target)`.

The comparison tests a structural capability rather than only throughput. The generator baselines must traverse preceding objects, while FinSpace addresses the target coordinate directly.

FinSpace access is repeated to reduce timer noise. Generator access is intentionally not cached.

## 5. Partition evidence

The suite evaluates several worker counts, including non-powers of two. For every worker count it verifies:

- first partition starts at zero;
- final partition ends at `N`;
- adjacent partitions meet exactly;
- total assigned object count equals `N`;
- maximum object-count imbalance is at most one.

This establishes coordinate coverage and non-overlap. It does not establish equal runtime across workers.

## 6. Checkpoint recovery

The recovery experiment executes the first 80 coordinates of a 200-object space and stops. A new `Runner` instance then reopens the same SQLite checkpoint and requests all 200 coordinates.

The evidence requires:

- 80 initially completed ranks;
- exactly 80 skipped ranks on resume;
- 120 newly completed ranks;
- exactly 200 completed records in the final store;
- zero duplicate ranks;
- zero missing ranks;
- zero result divergences relative to an uninterrupted deterministic reference calculation.

This is a controlled interruption/resume experiment. It does not simulate operating-system corruption or simultaneous multi-host SQLite writers.

## 7. Replay mismatch matrix

One canonical object and one execution are written to a `ReplayLedger`. The verifier is then presented with one-factor perturbations.

The required states are:

| Perturbation | Expected state |
|---|---|
| none | `reproduced` |
| adapter version | `adapter-mismatch` |
| environment | `environment-mismatch` |
| oracle configuration | `oracle-mismatch` |
| execution parameters | `execution-parameters-mismatch` |
| external-data identifier removed | `external-data-unavailable` |
| observed result changed | `result-divergence` |

The object itself must independently verify as `reconstructed`.

## 8. QuantLib case study

The QuantLib study builds a bounded European-option domain containing two currencies, multiple strikes/spots/maturities/volatilities, and all FinSpace-supported pricing engines.

Selected ranks are reconstructed and priced through the real `QuantLibEuropeanOptionPricer`. The evidence checks that returned numerical outputs are finite and records which pricing engines were exercised.

This demonstrates scenario orchestration and execution. It does not claim that FinSpace accelerates QuantLib's pricing kernels or that the chosen grid represents a market distribution.

## 9. FIX case study

The FIX study enumerates a bounded prefix of the real FinSpace New Order Single space and sends every reconstructed record through `SimpleFixNewOrderSingleEncoder`.

Each output must contain message type `35=D`, terminate correctly, and be generated from a schema-valid record. Order-type coverage is recorded.

The included schema is a bounded testing profile rather than a universal counterparty or exchange conformance profile.

## 10. ISO 20022 case study

The ISO 20022 study deliberately selects records from both bounded message families supported by FinSpace, pain.001 and pacs.008. Each record is reconstructed from a rank, generated through the actual adapter, and parsed as XML.

The evidence records both namespaces and requires both message families to be exercised.

This establishes deterministic bounded generation and XML well-formedness. It does not claim universal scheme-specific XSD conformance.

## 11. Negative controls

Evidence is incomplete unless known-bad cases fail. The suite therefore checks that:

- a FIX market order carrying an inactive limit-price field is rejected by the schema;
- a pain.001 record carrying a pacs.008-only priority field is rejected;
- an unsupported ISO message type is rejected by the adapter;
- an unsupported QuantLib engine is rejected;
- conditioned records remain valid in the parent space.

## 12. Interpretation rules

1. No single timing number should be presented as universal.
2. Small-domain losses to simpler baselines are valid negative results.
3. `tracemalloc` reports Python allocations, not total process RSS.
4. Results should be reproduced on the same commit before being quoted.
5. The generated `results.json` is the machine-readable source of truth for summary tables.
6. An experiment failure should fail CI rather than be silently omitted.
