# Versioning and schema migration

FinSpace has two distinct versioning problems and they should not be conflated.

## Package API versioning

The Python package follows semantic versioning. FinSpace 0.2.0 is a Beta API release. Public backward-incompatible changes require an explicit version change and changelog entry.

## Rank-space identity

A dense rank is meaningful only with the exact rank space retained. Durable records should preserve at least:

- FinSpace version;
- PDRS version;
- canonicalization version;
- schema hash;
- engine hash;
- rank.

Table constraints are part of the schema document and therefore part of the schema hash.

## Why ranks move

Adding a value, removing a value, reordering values, reordering fields, changing dependencies, or changing constraints can alter the enumeration order or the set of valid objects. FinSpace deliberately does not promise that the same integer continues to represent the same record after such edits.

## Migration maps

For bounded schemas, `compare_spaces(old, new)` enumerates canonical records under an explicit `max_objects` cap and reports:

- old rank to new rank mappings for surviving records;
- removed old ranks;
- added new ranks;
- stable-rank count;
- rank-churn count and fraction.

This makes schema evolution observable instead of pretending it is free.

```python
from finspace import compare_spaces

migration = compare_spaces(old_space, new_space)
for old_rank, new_rank in migration.mapping:
    assert old_space.unrank(old_rank) == new_space.unrank(new_rank)
```

The migration tool is intentionally bounded because it constructs a canonical-record index. Large production migrations should first narrow the domain, process an explicitly approved larger cap, or build a domain-specific migration procedure whose evidence can be audited independently.
