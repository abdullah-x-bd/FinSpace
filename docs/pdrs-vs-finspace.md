# PDRS and FinSpace

FinSpace uses PDRS as its exact rank/unrank engine, but the two projects solve different problems.

## Division of responsibility

| Capability | PDRS | FinSpace |
|---|---|---|
| General exact addressing of bounded dependent spaces | Primary contribution | Uses PDRS |
| Rank/unrank engine | Yes | Exposes through finance-facing `Space` |
| General dependency graph representation | Yes | Compiles finance schemas into it |
| Finance schema language and templates | No | Yes |
| Conditional financial fields | Generic mechanism only | Finance-facing schema semantics |
| QuantLib scenario integration | No | Yes |
| FIX message-space integration | No | Yes |
| ISO 20022 message-space integration | No | Yes |
| NumPy/pandas/Arrow financial batch conversion | No | Yes |
| Deterministic worker allocation API for finance campaigns | General primitives | Yes |
| SQLite checkpointed execution | No | Yes |
| Object identity tied to finance schema | No | Yes |
| Execution identity and replay ledger | No | Yes |
| Adapter/environment/oracle mismatch reporting | No | Yes |
| Finance-specific case studies and evidence | No | Yes |

## The PDRS contribution

PDRS addresses a general discrete-systems question:

> How can every valid object in a bounded path-dependent domain be assigned one exact integer coordinate and reconstructed from that coordinate?

It supplies the underlying exact counting and rank/unrank machinery.

## The FinSpace contribution

FinSpace addresses an application and orchestration question:

> How can dependent financial scenario and protocol domains be compiled onto exact coordinates and then used for deterministic sampling, work allocation, checkpointing, replay, and finance-library execution?

FinSpace therefore adds four layers above the general engine.

### 1. Finance-facing schema compilation

Users describe financial records through ordered fields, dependencies, conditions, templates, and metadata. `SchemaCompiler` converts that high-level model into a shared PDRS graph while retaining stable user-facing values and schema identity.

### 2. Campaign orchestration

`Space` and `Runner` turn ranks into operational coordinates for direct access, sampling, partitions, batches, checkpointing, and resumption.

### 3. External finance adapters

FinSpace maps canonical records into bounded QuantLib, FIX, and ISO 20022 workflows. Those integrations create execution concerns that are absent from a general rank/unrank engine.

### 4. Reproducibility semantics

FinSpace distinguishes reconstruction of a canonical object from reproduction of an execution. The replay ledger records adapter, environment, oracle, parameter, external-data, and result information and returns explicit mismatch states.

## What would make FinSpace merely a wrapper

FinSpace would be only a thin wrapper if it merely renamed PDRS functions and supplied finance examples. The repository therefore treats the following as independent evidence obligations:

- finance-schema compilation and validation;
- deterministic partition and checkpoint behaviour;
- interruption/resume equivalence;
- object-versus-execution replay semantics;
- QuantLib case-study execution;
- FIX dependent-message construction;
- ISO 20022 dependent-message construction;
- adversarial failure and mismatch detection.

These are exercised by the FinSpace evidence suite rather than inherited as claims from PDRS.

## Appropriate citation

Work using the general exact dependent-space method should cite PDRS when a citable PDRS release is available. Work specifically using FinSpace's finance schema, execution, adapters, replay ledger, or financial evidence should additionally cite FinSpace.
