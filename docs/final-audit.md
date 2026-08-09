# FinSpace final completion audit

FinSpace 0.2.0 is the completion point for the repository-level research-software programme described here. “Complete” means that every in-scope claim has an implementation, tests, CI enforcement, and reproducible evidence where empirical evidence is appropriate. It does not mean that independent adoption, external reproduction, or upstream PDRS research questions can be self-certified by this repository.

## Steps 1 through 15

| Step | Result | Permanent artifact |
|---:|---|---|
| 1 | Freeze claims and non-claims | `docs/claims.md` |
| 2 | Separate PDRS and FinSpace contributions | `docs/pdrs-vs-finspace.md` |
| 3 | Add property-level correctness tests | `tests/test_properties.py` |
| 4 | Enforce 90% branch-aware semantic-core coverage | `.coveragerc-core`, CI |
| 5 | Add adversarial dependent schemas | `tests/test_adversarial_schemas.py` |
| 6 | Measure compilation/domain scaling | `experiments/reproduce.py` |
| 7 | Add Cartesian and recursive baselines | `experiments/reproduce.py` |
| 8 | Measure direct rank random access | `experiments/reproduce.py` |
| 9 | Prove deterministic partition coverage empirically | partition tests and evidence |
| 10 | Test interruption and checkpoint recovery | runner tests and evidence |
| 11 | Add adversarial replay mismatch matrix | replay tests and evidence |
| 12 | Execute QuantLib, FIX, and ISO 20022 case studies | integration CI and evidence |
| 13 | Add deliberate invalid controls | `tests/test_negative_controls.py` |
| 14 | Build one-command reproducible evidence | `experiments/reproduce.py` |
| 15 | Publish a measured positive-and-negative evidence report | `evidence/EVIDENCE_REPORT.md` |

## Steps 16 through 30

| Step | Result | Permanent artifact |
|---:|---|---|
| 16 | Add exact integer-weight sampling | `src/finspace/weighted.py`, `tests/test_weighted.py` |
| 17 | Add contiguous, strided, and deterministic mixed allocation | `src/finspace/allocation.py`, allocation tests |
| 18 | Add explicit schema compatibility and rank-churn maps | `src/finspace/evolution.py`, evolution tests |
| 19 | Add richer exact finite cross-field constraints | `TableConstraint`, compiler pruning, constraint tests |
| 20 | Add deterministic automatic failure shrinking | `src/finspace/shrink.py`, shrink tests |
| 21 | Add integrity-protected rank handles | `src/finspace/identity.py`, checksum/MAC tests |
| 22 | Add versioned campaign manifests and semantic digests | `src/finspace/campaign.py` |
| 23 | Add execution retries with attempt provenance | `Runner(max_retries=...)` and retry tests |
| 24 | Add checkpoint failure/status introspection | `CheckpointStore.failed_ranks`, `status_counts` |
| 25 | Add cluster-neutral portable shard manifests | `src/finspace/cluster.py`, shard tests |
| 26 | Add generic invalid-record mutation generation | `src/finspace/mutations.py`, mutation tests |
| 27 | Add a second falsifiable evidence campaign | `experiments/final_hardening.py` |
| 28 | Add SHA-256 manifests and deterministic evidence archives | `src/finspace/artifact.py`, artifact tests |
| 29 | Freeze 0.2.0 API/version/release discipline | `pyproject.toml`, `CHANGELOG.md`, versioning docs |
| 30 | Run complete final audit, CI, and reproducible 1-30 package | `experiments/final_reproduce.py`, CI, this audit |

## Final quality contract

A FinSpace 0.2.0 change is not considered release-ready unless all of the following pass together:

- Ruff over source, tests, and experiments.
- Strict mypy over the complete semantic core.
- Python 3.11, 3.12, and 3.13 tests.
- At least 90% branch-aware semantic-core coverage.
- Published PDRS 0.2.0 compatibility smoke test.
- Source distribution and wheel build verification.
- Installed-wheel smoke test exposing the 0.2.0 API.
- Real optional-finance integration tests.
- Generic invalid-record controls.
- Complete `python -m experiments.final_reproduce --output evidence/generated` evidence package.
- SHA-256 artifact verification and deterministic archive construction.

## What “finished” deliberately does not mean

Three categories remain outside the FinSpace 0.2.0 completion claim.

### Upstream PDRS research

Bounded recursive grammar support, native-runtime extensions, and proof-assistant mechanization change the underlying rank-space engine or its mathematical formalization. They belong to PDRS rather than the finance-facing FinSpace repository. FinSpace 0.2.0 therefore does not imitate those features locally or create a second incompatible core.

### External validation

Independent reproduction, third-party adoption, historical defect discovery, anonymized institutional workloads, and external benchmark contributions require independent actors. The repository supplies a deterministic artifact and reproduction command so those checks can occur, but it cannot honestly certify independence itself.

### Permanent archival services

A DOI from Zenodo or another archive is valuable for a paper artifact, but creation of a third-party archival record is an external publication action rather than a software-correctness property. The deterministic ZIP, checksums, versions, and commit identity make the repository ready for such archiving without claiming that a DOI already exists.

## Final reproducibility command

```bash
python -m experiments.final_reproduce --output evidence/generated
```

The command reruns the original evidence, executes the final-hardening experiments, verifies the generated SHA-256 manifest, and creates a deterministic evidence archive.
