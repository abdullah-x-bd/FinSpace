# Scheduler-neutral distributed shards

FinSpace 0.2 separates **rank allocation** from **cluster transport**.

A `ShardManifest` records the schema hash, engine hash, object count, worker number, worker count, allocation strategy, seed, and expected allocation size. The manifest can be serialized by an application and handed to a Ray task, Dask worker, Spark partition, Kubernetes Job, Slurm job, or another scheduler without making any of those systems a FinSpace runtime dependency.

```python
from finspace import build_shard_manifests, execute_shard

shards = build_shard_manifests(
    space,
    worker_count=32,
    strategy="permuted",
    seed=7,
)

# Inside the worker process after the application transports one manifest:
summary = execute_shard(space, evaluate, shards[worker_id], checkpoint=checkpoint_path)
```

## Allocation strategies

### Contiguous

Each worker receives one half-open interval. This is the simplest representation and preserves locality in canonical rank order.

### Strided

Worker `w` receives ranks `w, w + W, w + 2W, ...`. This mixes adjacent canonical regions while remaining trivial to reconstruct.

### Permuted

The global logical index is mapped through a deterministic affine bijection before assignment. This mixes rank regions while preserving exact union and non-overlap. It is intended for reproducible workload mixing, not cryptographic secrecy.

## Failure and retry semantics

External schedulers may retry whole tasks. Within one shard, FinSpace can also retry an individual failing callable via `Runner(max_retries=...)`. Attempt counts are persisted in checkpoints. Completed ranks are skipped on compatible resume while failed ranks remain eligible for later execution.

## What is and is not validated

The repository tests shard construction, exact coverage, non-overlap, manifest/space identity checks, and local execution through the standard Runner. It intentionally does **not** claim that every version or deployment topology of Ray, Dask, Spark, Kubernetes, Slurm, or another scheduler has been validated.

The scheduler-neutral boundary avoids turning infrastructure-specific behavior into a FinSpace semantic dependency.
