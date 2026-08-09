from __future__ import annotations

from hypothesis import given, settings, strategies as st

from finspace import Condition, Field, RecordValidationError, Schema, Space


def _orders() -> Space:
    return Space(
        Schema(
            name="property-orders",
            fields=(
                Field.enum("order_type", ("market", "limit", "stop_limit")),
                Field.enum("symbol", ("AAPL", "MSFT", "NVDA")),
                Field.enum(
                    "price",
                    (90, 100, 110),
                    when=(Condition("order_type", ("limit", "stop_limit")),),
                ),
                Field.enum(
                    "stop",
                    (80, 90),
                    when=(Condition("order_type", ("stop_limit",)),),
                ),
            ),
        )
    )


ORDERS = _orders()


@settings(max_examples=150, deadline=None)
@given(st.integers(min_value=0, max_value=ORDERS.count - 1))
def test_rank_unrank_are_inverse_for_every_generated_rank(rank: int) -> None:
    record = ORDERS.unrank(rank)
    assert ORDERS.rank(record) == rank
    assert ORDERS.unrank(ORDERS.rank(record)) == record


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=0, max_value=ORDERS.count - 1))
def test_every_unranked_record_validates(rank: int) -> None:
    assert ORDERS.validate(ORDERS.unrank(rank))


@settings(max_examples=100, deadline=None)
@given(
    st.integers(min_value=0, max_value=2**63 - 1),
    st.integers(min_value=0, max_value=ORDERS.count),
)
def test_no_replacement_sampling_is_seeded_unique(seed: int, n: int) -> None:
    first = ORDERS.sample(n, replace=False, seed=seed, with_ranks=True)
    second = ORDERS.sample(n, replace=False, seed=seed, with_ranks=True)
    assert first == second
    assert len({rank for rank, _ in first}) == n


@settings(max_examples=75, deadline=None)
@given(st.integers(min_value=1, max_value=32))
def test_partitions_are_exact_for_arbitrary_worker_counts(worker_count: int) -> None:
    partitions = ORDERS.partitions(worker_count)
    assert partitions[0].start == 0
    assert partitions[-1].stop == ORDERS.count
    assert sum(len(partition) for partition in partitions) == ORDERS.count
    for left, right in zip(partitions, partitions[1:], strict=False):
        assert left.stop == right.start
    sizes = [len(partition) for partition in partitions]
    assert max(sizes) - min(sizes) <= 1


@settings(max_examples=75, deadline=None)
@given(st.sampled_from(("market", "limit", "stop_limit")))
def test_conditioning_returns_parent_valid_records(order_type: str) -> None:
    conditioned = ORDERS.condition(order_type=order_type)
    for record in conditioned.enumerate():
        assert record["order_type"] == order_type
        assert ORDERS.unrank(ORDERS.rank(record)) == record


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(("AAPL", "MSFT", "NVDA")), st.integers(min_value=1, max_value=10000))
def test_inactive_market_price_is_always_rejected(symbol: str, price: int) -> None:
    record = {"order_type": "market", "symbol": symbol, "price": price}
    try:
        ORDERS.rank(record)
    except RecordValidationError:
        return
    raise AssertionError("inactive market price was accepted")


def test_schema_hash_is_stable_for_identical_schema_and_sensitive_to_changes() -> None:
    first = Schema(name="hash", fields=(Field.enum("x", (1, 2, 3)), Field.enum("y", ("a", "b"))))
    same = Schema(name="hash", fields=(Field.enum("x", (1, 2, 3)), Field.enum("y", ("a", "b"))))
    changed_values = Schema(
        name="hash", fields=(Field.enum("x", (1, 2, 4)), Field.enum("y", ("a", "b")))
    )
    changed_order = Schema(
        name="hash", fields=(Field.enum("y", ("a", "b")), Field.enum("x", (1, 2, 3)))
    )
    assert first.hash == same.hash
    assert first.hash != changed_values.hash
    assert first.hash != changed_order.hash


def test_enumeration_is_complete_and_unique() -> None:
    records = list(ORDERS.enumerate())
    ranks = [ORDERS.rank(record) for record in records]
    assert ranks == list(range(ORDERS.count))
    assert len(records) == ORDERS.count
