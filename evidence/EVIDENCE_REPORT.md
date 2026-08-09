# FinSpace Evidence Report

This report records the first complete research-software evidence campaign for FinSpace 0.1. The measurements below come from a GitHub-hosted Ubuntu CI reference run using Python 3.12.13. They are intended to establish correctness, scaling structure, direct addressability, recovery semantics, replay behaviour, and bounded finance integration. They are not universal performance guarantees.

The machine-readable source of truth is produced by:

```bash
python -m experiments.reproduce --output evidence/generated
```

The full protocol is documented in [`docs/benchmark-methodology.md`](../docs/benchmark-methodology.md), and the claim boundaries are fixed in [`docs/claims.md`](../docs/claims.md).

## 1. Claim status

| Evidence family | Result |
|---|---|
| Dependent-space compilation | PASS |
| Independent enumeration agreement | PASS |
| Rank-addressed random access | PASS |
| Deterministic partition coverage | PASS |
| Checkpoint interruption and resume | PASS |
| Object reconstruction | PASS |
| Execution mismatch classification | PASS |
| QuantLib case study | PASS |
| FIX case study | PASS |
| ISO 20022 case study | PASS |
| Deliberately invalid controls | PASS |

## 2. Compiler scaling

The synthetic scaling family increases the number of currencies, valid currency-dependent rates, spots, strikes, and maturities while preserving a shared dependent structure. The suite records the number of complete valid objects without materializing them.

| Profile size | Cartesian candidates | Valid logical objects | Compiled states | Compile time, s | Peak Python allocation, bytes |
|---:|---:|---:|---:|---:|---:|
| 2 | 256 | 192 | 7 | 0.00177 | 31,498 |
| 4 | 4,096 | 2,560 | 9 | 0.00255 | 42,580 |
| 8 | 65,536 | 36,864 | 13 | 0.00501 | 81,048 |
| 12 | 331,776 | 179,712 | 17 | 0.00811 | 127,960 |
| 16 | 1,048,576 | 557,056 | 21 | 0.01208 | 187,178 |
| 24 | 5,308,416 | 2,764,800 | 29 | 0.02262 | 345,302 |
| 32 | 16,777,216 | **8,650,752** | **37** | 0.03550 | 543,058 |

The important structural result is not the wall-clock time. It is that the largest tested logical domain contains more than 8.6 million valid complete objects while the compiled representation contains 37 states. This supports the repository's state-sharing claim for this dependency family.

It does not prove that every financial schema compresses similarly. Schemas with little reusable suffix structure can produce substantially larger compiled graphs.

## 3. Full enumeration baselines

The evidence suite compares three streaming implementations over exactly the same valid objects:

1. Cartesian product followed by dependency filtering;
2. a hand-written dependency-aware recursive generator;
3. `FinSpace.enumerate()`.

| Profile | Valid objects | Cartesian filter, s | Recursive generator, s | FinSpace enumeration, s |
|---:|---:|---:|---:|---:|
| 2 | 192 | 0.000098 | 0.000093 | 0.00863 |
| 4 | 2,560 | 0.00290 | 0.00238 | 0.13126 |
| 6 | 12,096 | 0.01479 | 0.01145 | 0.69965 |
| 8 | 36,864 | 0.05330 | 0.03934 | 2.35046 |

This is a deliberate negative result: **FinSpace is slower than the simple generators for full sequential traversal in this Python benchmark.**

That does not contradict the core claim. FinSpace pays compilation and reconstruction overhead in exchange for exact coordinate addressing, conditioning, deterministic allocation, checkpoint coordinates, and direct access. The benchmark therefore rejects any claim that FinSpace is a universally faster enumerator.

## 4. Direct random access

The same profile-size-8 domain contains 36,864 valid objects. The experiment retrieves the first, middle, and final valid object either by scanning a generator or directly through `Space.unrank(rank)`.

| Rank | Cartesian scan | Recursive scan | FinSpace direct unrank |
|---:|---:|---:|---:|
| 0 | 6.18 µs | 2.44 µs | 10.82 µs median |
| 18,432 | 3.52 ms | 0.849 ms | 16.70 µs median |
| 36,863 | 6.10 ms | 1.689 ms | **19.00 µs median** |

At rank zero the simple generators are faster because no traversal is required. By the middle and end of the domain, direct rank access avoids scanning all prior valid objects. The final-rank comparison in this reference run was approximately:

- 321 times faster than Cartesian filtering;
- 89 times faster than the recursive generator.

These ratios are reference-run observations, not universal guarantees.

## 5. Deterministic partitioning

A 179,712-object domain was partitioned among 1, 2, 3, 7, 16, 32, 64, and 128 workers.

For every worker count:

- the first interval started at zero;
- the final interval ended at 179,712;
- every adjacent pair met exactly;
- the sum of worker object counts equalled 179,712;
- no overlap or omission was observed;
- maximum object-count imbalance was at most one.

The 7-worker case produced worker sizes of 25,673 or 25,674 objects. All tested evenly divisible worker counts had zero object-count imbalance.

This establishes exact coordinate allocation. It does not establish equal execution time per worker.

## 6. Checkpoint interruption and resume

A deterministic 200-object campaign was intentionally split into two executions.

### First execution

- requested ranks: 0 through 79;
- submitted: 80;
- completed: 80;
- failed: 0.

### Resumed execution

The same run ID and checkpoint then requested all 200 ranks.

- submitted: 200;
- previously completed and skipped: **80**;
- newly completed: **120**;
- failed: 0;
- completed records in final checkpoint: **200**;
- duplicate rank records: **0**;
- missing ranks: **0**;
- result divergences against uninterrupted deterministic reference: **0**.

Result: **PASS**.

The experiment establishes local SQLite checkpoint and resume semantics. It does not claim multi-host transactional coordination or resilience to arbitrary filesystem corruption.

## 7. Replay and reproduction mismatch matrix

The replay experiment writes one canonical object identity and one execution identity to `ReplayLedger`, then changes one execution-relevant factor at a time.

| Trial | Observed state | Expected state |
|---|---|---|
| unchanged object | `reconstructed` | `reconstructed` |
| unchanged execution | `reproduced` | `reproduced` |
| adapter version changed | `adapter-mismatch` | `adapter-mismatch` |
| environment changed | `environment-mismatch` | `environment-mismatch` |
| oracle configuration changed | `oracle-mismatch` | `oracle-mismatch` |
| execution parameters changed | `execution-parameters-mismatch` | `execution-parameters-mismatch` |
| external-data identifier unavailable | `external-data-unavailable` | `external-data-unavailable` |
| observed result changed | `result-divergence` | `result-divergence` |

Every expected state was returned exactly. Result: **PASS**.

This supports FinSpace's distinction between reconstructing the object that was evaluated and establishing that a later execution was performed under equivalent computational conditions.

## 8. QuantLib case study

A bounded European-option domain containing:

- USD and EUR;
- multiple spots and strikes;
- multiple maturities;
- multiple volatilities and rates;
- three pricing-engine choices;

contained **864 exact FinSpace scenarios**.

Ten deliberately distributed ranks were reconstructed and evaluated through the actual QuantLib adapter. The run exercised:

- `analytic`;
- `binomial`;
- `finite_difference`.

All checked numerical outputs were finite where the adapter exposes them. Result: **PASS**.

The experiment demonstrates bounded scenario construction, rank reconstruction, and adapter execution. It does not claim that FinSpace accelerates QuantLib's pricing kernels or that the scenario grid represents market probabilities.

## 9. FIX case study

The built-in bounded New Order Single domain contains **8,640 exact records**. The reference run reconstructed and encoded 100 ranks through `SimpleFixNewOrderSingleEncoder`.

For every executed record:

- the payload contained message type `35=D`;
- the message terminated with the FIX delimiter;
- the input record had already passed FinSpace schema validation.

Encoded message sizes in this run ranged from 169 to 173 bytes. Result: **PASS**.

The reference rank prefix happened to contain only FIX order type `1`. Consequently this first evidence run establishes adapter execution and record validity for that sampled prefix, but it should not be interpreted as cross-order-type protocol coverage. Cross-order-type sampling is a useful subsequent extension.

The FinSpace FIX profile is intentionally bounded and is not represented as a universal exchange or counterparty production profile.

## 10. ISO 20022 case study

The bounded payment space contains **57,600 exact records**. The evidence suite intentionally selected examples from both supported message families and executed 60 records in total.

Observed message families:

- `pain.001.001.13`;
- `pacs.008.001.14`.

Observed namespaces:

- `urn:iso:std:iso:20022:tech:xsd:pain.001.001.13`;
- `urn:iso:std:iso:20022:tech:xsd:pacs.008.001.14`.

Every generated payload parsed successfully as XML and had the expected Document root structure. Result: **PASS**.

This establishes deterministic bounded generation and XML well-formedness. It does **not** establish universal bank, network, scheme, or production XSD conformance.

## 11. Negative controls

The evidence suite deliberately presents conditions the system should reject.

| Negative control | Result |
|---|---|
| FIX market order given an inactive price field | rejected, PASS |
| pain.001 record given a pacs.008-only priority field | rejected, PASS |
| unsupported ISO 20022 message type | rejected, PASS |
| unsupported QuantLib pricing engine | rejected, PASS |
| conditioned FIX records checked against parent domain | valid, PASS |

The replay mismatch matrix in Section 7 provides additional negative controls for reproducibility claims.

## 12. Correctness test layer

Separate from the benchmark campaign, the repository now includes:

- property-based rank/unrank inversion tests;
- property-based deterministic sampling tests;
- arbitrary worker-count partition tests;
- conditioning invariants;
- schema-hash stability and sensitivity tests;
- adversarial dependent and inactive-field schemas;
- impossible-conditioning tests;
- invalid dependency-order tests;
- semantic edge tests for schema validation;
- runner failure and checkpoint edge tests;
- replay identity and mismatch edge tests.

The permanent CI quality gate requires at least **90% branch-aware coverage of the semantic FinSpace core**. CLI, batch conversion, templates, and external finance adapters are validated through separate smoke and integration paths so that the core coverage number does not conflate unavailable optional dependencies with semantic correctness.

## 13. Interpretation

The first complete evidence campaign supports a narrower and more defensible description of FinSpace:

> FinSpace is a validated research-software system for exact coordinate addressing, deterministic allocation, checkpointing, and replay over bounded dependent financial scenario and protocol spaces.

The campaign also identifies an important non-result: FinSpace is not a faster general-purpose full enumerator than a compact hand-written recursive generator in the tested Python workloads. Its measured advantage appears where coordinate addressability, random access, resumption, work allocation, and execution identity matter.

## 14. Reproduction

Install the complete evidence environment:

```bash
python -m pip install --upgrade pip
python -m pip install --no-cache-dir pdrs==0.2.0
python -m pip install -e ".[dev,all]"
```

Run:

```bash
python -m experiments.reproduce --output evidence/generated
```

or:

```bash
make evidence
```

Generated outputs include:

- `results.json`;
- `scalability.csv`;
- `baselines.csv`;
- `random_access.csv`;
- `partitions.csv`;
- `SUMMARY.md`.

GitHub CI also uploads the generated evidence directory as a workflow artifact.

## 15. Remaining claim boundaries

This report does not establish:

- market-realistic sampling probabilities;
- equal worker runtime;
- arbitrary weighted-domain sampling;
- universal FIX or ISO 20022 production conformance;
- cryptographic integrity of ranks;
- rank stability across arbitrary schema changes;
- deterministic external results when external market data, calendars, libraries, or environments cannot be reconstructed;
- universal speedup over simpler generation approaches.

Those boundaries are intentional. FinSpace's research value depends on keeping the claim surface narrower than the implementation surface.