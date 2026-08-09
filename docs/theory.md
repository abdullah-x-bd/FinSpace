# FinSpace formal model

This note defines the abstractions used by FinSpace precisely enough to state correctness and reproducibility claims without turning the repository into a mathematics paper.

## 1. Finite dependent schema

A FinSpace schema is an ordered sequence of fields

`F = (F_1, F_2, ..., F_d)`

where each active field has a finite set of admissible values. The admissible values of field `F_i` may depend on values assigned to earlier fields. A field may also be inactive under some earlier assignments.

A complete record is valid when every active field is present, every inactive field is absent, and every value belongs to the field's admissible set under the preceding context.

Let `V(S)` denote the finite set of valid canonical records under schema `S`. Let

`N(S) = |V(S)|`.

## 2. Exact rank and unrank

For a fixed schema and canonicalization version, FinSpace exposes two maps:

`rank_S : V(S) -> {0, ..., N(S)-1}`

and

`unrank_S : {0, ..., N(S)-1} -> V(S)`.

The central correctness property is that these maps are inverses:

`unrank_S(rank_S(x)) = x`

for every canonical valid record `x`, and

`rank_S(unrank_S(i)) = i`

for every rank `i` in the domain.

Consequences include uniqueness of ranks and complete enumeration by iterating integer coordinates.

## 3. Canonicalization and schema identity

User-facing values are converted to a deterministic canonical representation before schema hashing and branch comparison. The public `schema_hash` identifies the exact high-level FinSpace schema. The `engine_hash` identifies the compiled PDRS graph.

Ranks are meaningful only together with the exact schema and canonicalization version. A rank by itself is deliberately not treated as a global identifier.

## 4. Dependency contexts and state sharing

A naive tree representation can duplicate identical suffix structure after different prefixes. The FinSpace compiler determines which previously assigned fields can affect each remaining suffix and memoizes states by that relevant context.

If a suffix is independent of `currency`, for example, branches reached through USD and EUR can share that suffix state. Compilation cost therefore tracks distinct dependency contexts rather than the raw number of complete records.

The evidence suite reports both logical domain cardinality and compiled-state count across synthetic dependent spaces.

## 5. Conditioning

Given schema `S` and a compatible partial assignment `c`, `condition(c)` constructs the subspace

`V(S | c) = {x in V(S) : x agrees with c}`.

A conditioned FinSpace remains rank-addressable in its own local coordinate system. Records returned from the subspace remain valid records of the parent schema.

## 6. Sampling

`sample(n, replace=False)` samples integer coordinates without replacement and reconstructs the corresponding objects. With a fixed seed and package/schema version, the selected coordinate sequence is deterministic.

`sample_stratified(field, n)` targets approximately balanced allocation across values of one named field. It is a coverage-oriented operation, not a probability model for the financial world.

## 7. Deterministic partitions

For `W > 0` workers and worker `w` in `{0, ..., W-1}`, FinSpace assigns the half-open interval

`[ floor(wN/W), floor((w+1)N/W) )`.

These intervals are disjoint, adjacent, and collectively cover `[0, N)`. Their object counts differ by at most one.

This provides deterministic ownership of object coordinates. It does not account for heterogeneous execution time per object.

## 8. Checkpoint semantics

A checkpoint records execution status by run identifier, schema identity, engine identity, rank, result, traceback, and elapsed time. On a compatible resume, ranks recorded as completed are skipped. Failed ranks remain eligible for later execution.

The evidence suite compares an interrupted-and-resumed campaign with an uninterrupted reference campaign.

## 9. Object identity

An object identity binds at least:

`canonicalization version || schema hash || rank || PDRS version/commit`.

This is intended to answer:

> Which canonical object was this?

Given the retained schema and compatible software, the rank can reconstruct the object.

## 10. Execution identity

An execution identity additionally binds:

`FinSpace version/commit || adapter || environment || oracle configuration || execution parameters || external-data snapshot`.

This is intended to answer a stronger question:

> Under what computational conditions was this object executed, and does a later execution match those conditions and result?

FinSpace deliberately returns explicit mismatch states rather than collapsing these questions into a single `reproduced` claim.

## 11. Finance layer

The finance layer maps canonical finite records into external-domain objects or calculations. Current bounded adapters include:

- European-option pricing through QuantLib;
- FIX New Order Single message generation through SimpleFIX;
- bounded pain.001 and pacs.008 XML generation for ISO 20022 workflows.

The adapter boundary is where FinSpace's finite scenario identity meets external computational semantics. Full execution reproducibility therefore requires more information than rank and schema alone.

## 12. Complexity interpretation

Let `C` be the number of distinct relevant dependency contexts in the compiled graph, `d` the active field depth, and `N` the number of valid complete objects.

FinSpace is designed so that the compiled representation can be much smaller than `N` when suffix structure is shared. Rank and unrank operate over active depth and compiled branch metadata rather than enumerating all earlier objects.

No universal constant-factor speedup is claimed. The benchmark suite separately measures compilation, streaming enumeration, and random access against simple baselines.