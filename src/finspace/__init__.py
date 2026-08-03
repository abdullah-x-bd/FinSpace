"""FinSpace: exact, rank-addressable financial scenario spaces."""

from .batch import records_to_columns, to_arrow, to_numpy, to_pandas
from .errors import (
    CheckpointError,
    FinSpaceError,
    MissingOptionalDependency,
    RankOutOfRangeError,
    RecordValidationError,
    SchemaDefinitionError,
)
from .replay import (
    CANONICALIZATION_VERSION,
    ExecutionIdentity,
    ObjectIdentity,
    ReplayLedger,
    build_execution_identity,
    build_object_identity,
    environment_manifest,
)
from .schema import Case, Condition, Field, Schema
from .space import Partition, Space

__all__ = [
    "CANONICALIZATION_VERSION",
    "Case",
    "CheckpointError",
    "Condition",
    "ExecutionIdentity",
    "Field",
    "FinSpaceError",
    "MissingOptionalDependency",
    "ObjectIdentity",
    "Partition",
    "RankOutOfRangeError",
    "RecordValidationError",
    "ReplayLedger",
    "Schema",
    "SchemaDefinitionError",
    "Space",
    "build_execution_identity",
    "build_object_identity",
    "environment_manifest",
    "records_to_columns",
    "to_arrow",
    "to_numpy",
    "to_pandas",
]

__version__ = "0.1.0"
