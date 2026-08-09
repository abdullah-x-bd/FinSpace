# Release and deployment

## Release gate

A FinSpace 0.2 release candidate is acceptable only after the permanent GitHub Actions matrix passes on the exact candidate commit. The gate includes linting, strict semantic-core typing, Python 3.11 through 3.13 tests, at least 90% branch-aware semantic-core coverage, package build and wheel smoke tests, optional-finance integrations, and the complete evidence package.

## Reproduce before building

```bash
python -m experiments.final_reproduce --output evidence/generated
```

The generated directory must contain the ordinary evidence outputs plus:

- `final_hardening.json`
- `MANIFEST.json`
- `SHA256SUMS.txt`
- `finspace-evidence.zip`

The manifest verifies the generated evidence files before the archive is created.

## Build

```bash
python -m build
python -m twine check dist/*
```

## Verify the wheel

```bash
python -m venv /tmp/finspace-wheel
/tmp/finspace-wheel/bin/pip install dist/finspace-*.whl
/tmp/finspace-wheel/bin/finspace --version
/tmp/finspace-wheel/bin/python -c "import finspace; assert finspace.__version__ == '0.2.0'"
```

## Versioning

FinSpace follows semantic versioning for its public Python API. Schema-relative behavior has a stricter identity rule:

- a schema hash identifies the exact declarative schema, including table constraints;
- the engine hash identifies the compiled PDRS document;
- the canonicalization version is part of replay identity;
- ranks are meaningful only with those identities retained;
- arbitrary schema edits are expected to change hashes and may change ranks;
- `compare_spaces` can construct a bounded canonical-record migration map where records survive an edit.

FinSpace 0.2 is a Beta release. Backward-incompatible API changes after 0.2 require an explicit changelog entry and a version change. A schema or canonicalization change must never be presented as rank-stable merely because records look similar.

## PyPI prerequisites

The `pdrs` distribution must be published before a public `finspace` wheel that declares it as a runtime dependency. The candidate must be tested against the exact minimum PDRS version used in CI.

Publishing to PyPI, creating a GitHub release tag, or depositing a DOI archive are release-owner actions. Passing this repository's release gate makes the candidate ready for those actions but does not perform or imply them.

## Recommended campaign record

Prefer a `CampaignManifest` plus protected rank handles for durable campaign records. At minimum retain:

```json
{
  "finspace_version": "0.2.0",
  "pdrs_version": "0.2.0",
  "canonicalization_version": "2",
  "schema_hash": "...",
  "engine_hash": "...",
  "rank": 123456,
  "selection": {"strategy": "permuted", "seed": 7},
  "adapter_name": "...",
  "adapter_version": "...",
  "environment_hash": "...",
  "oracle_config_hash": "...",
  "external_data_snapshot": "..."
}
```

For accidental-corruption detection, use a checksum rank handle. Where authenticity is required, use an HMAC rank handle and manage the key outside FinSpace according to the deployment's security policy.

## Archival checklist

For a paper or permanent artifact release retain:

1. the exact Git commit SHA;
2. source and wheel artifacts;
3. `finspace-evidence.zip`;
4. `MANIFEST.json` and `SHA256SUMS.txt`;
5. the CI run identifier;
6. exact PDRS and FinSpace versions;
7. any external-data snapshots or immutable snapshot identifiers;
8. a DOI only after an external archive has actually issued one.
