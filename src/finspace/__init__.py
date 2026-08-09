"""FinSpace: exact, rank-addressable financial scenario spaces."""

from .allocation import RankAllocation, allocations, permute_rank
from .artifact import (
    ArtifactEntry,
    build_artifact_manifest,
    build_reproducible_zip,
    sha256_file,
    verify_artifact_manifest,
    write_manifest,
    write_sha256sums,
)
from .batch import records_to_columns, to_arrow, to_numpy, to_pandas
from .campaign import CampaignManifest, build_campaign_manifest
from .cluster import ShardManifest, build_shard_manifests, execute_shard
from .errors import (
    CheckpointError,
    FinSpaceError,
    MissingOptionalDependency,
    RankOutOfRangeError,
    RecordValidationError,
    SchemaDefinitionError,
)
from .evolution import MigrationMap, compare_spaces
from .identity import RankHandle, create_rank_handle, parse_rank_handle
from .mutations import RecordMutation, invalid_mutations
from .replay import (
    CANONICALIZATION_VERSION,
    ExecutionIdentity,
    ObjectIdentity,
    ReplayLedger,
    build_execution_identity,
    build_object_identity,
    environment_manifest,
)
from .schema import Case, Condition, Field, Schema, TableConstraint
from .shrink import ShrinkResult, shrink_failure
from .space import Partition, Space
from .weighted import WeightedSampler

__all__ = [
    "CANONICALIZATION_VERSION",
    "ArtifactEntry",
    "CampaignManifest",
    "Case",
    "CheckpointError",
    "Condition",
    "ExecutionIdentity",
    "Field",
    "FinSpaceError",
    "MigrationMap",
    "MissingOptionalDependency",
    "ObjectIdentity",
    "Partition",
    "RankAllocation",
    "RankHandle",
    "RankOutOfRangeError",
    "RecordMutation",
    "RecordValidationError",
    "ReplayLedger",
    "Schema",
    "SchemaDefinitionError",
    "ShardManifest",
    "ShrinkResult",
    "Space",
    "TableConstraint",
    "WeightedSampler",
    "allocations",
    "build_artifact_manifest",
    "build_campaign_manifest",
    "build_execution_identity",
    "build_object_identity",
    "build_reproducible_zip",
    "build_shard_manifests",
    "compare_spaces",
    "create_rank_handle",
    "environment_manifest",
    "execute_shard",
    "invalid_mutations",
    "parse_rank_handle",
    "permute_rank",
    "records_to_columns",
    "sha256_file",
    "shrink_failure",
    "to_arrow",
    "to_numpy",
    "to_pandas",
    "verify_artifact_manifest",
    "write_manifest",
    "write_sha256sums",
]

__version__ = "0.2.0"
