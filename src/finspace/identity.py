"""Integrity-protected, schema-bound rank handles."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Literal, cast

from .space import Space

HANDLE_VERSION = "1"
HandleMode = Literal["checksum", "mac"]


def _payload(version: str, schema_hash: str, rank: int) -> bytes:
    return f"{version}:{schema_hash}:{rank}".encode("utf-8")


def _checksum(payload: bytes) -> str:
    return hashlib.blake2s(payload, digest_size=8).hexdigest()


def _mac(payload: bytes, key: bytes) -> str:
    if not key:
        raise ValueError("MAC key cannot be empty")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()[:32]


@dataclass(frozen=True)
class RankHandle:
    """A portable schema hash + rank coordinate with optional authentication."""

    version: str
    schema_hash: str
    rank: int
    mode: HandleMode
    integrity: str

    def encode(self) -> str:
        return f"fs{self.version}.{self.schema_hash}.{self.rank}.{self.mode}.{self.integrity}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "schema_hash": self.schema_hash,
            "rank": self.rank,
            "mode": self.mode,
            "integrity": self.integrity,
            "encoded": self.encode(),
        }

    def verify(self, space: Space, *, key: bytes | None = None) -> bool:
        if self.version != HANDLE_VERSION:
            return False
        if self.schema_hash != space.schema_hash:
            return False
        if self.rank < 0 or self.rank >= space.count:
            return False
        payload = _payload(self.version, self.schema_hash, self.rank)
        if self.mode == "checksum":
            expected = _checksum(payload)
        else:
            if key is None:
                return False
            expected = _mac(payload, key)
        return hmac.compare_digest(self.integrity, expected)


def create_rank_handle(space: Space, rank: int, *, key: bytes | None = None) -> RankHandle:
    space.unrank(rank)
    payload = _payload(HANDLE_VERSION, space.schema_hash, rank)
    if key is None:
        return RankHandle(HANDLE_VERSION, space.schema_hash, rank, "checksum", _checksum(payload))
    return RankHandle(HANDLE_VERSION, space.schema_hash, rank, "mac", _mac(payload, key))


def parse_rank_handle(value: str) -> RankHandle:
    parts = value.split(".")
    if len(parts) != 5 or not parts[0].startswith("fs"):
        raise ValueError("invalid FinSpace rank handle")
    version = parts[0][2:]
    schema_hash = parts[1]
    if len(schema_hash) != 64 or any(ch not in "0123456789abcdef" for ch in schema_hash.lower()):
        raise ValueError("invalid schema hash in rank handle")
    try:
        rank = int(parts[2])
    except ValueError as error:
        raise ValueError("invalid rank in FinSpace handle") from error
    mode = parts[3]
    if mode not in {"checksum", "mac"}:
        raise ValueError("invalid FinSpace handle integrity mode")
    integrity = parts[4]
    if not integrity:
        raise ValueError("missing FinSpace handle integrity value")
    return RankHandle(version, schema_hash, rank, cast(HandleMode, mode), integrity)
