from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from finspace import RecordValidationError, Schema, Space
from finspace.adapters import ISO20022PaymentBuilder, QuantLibEuropeanOptionPricer
from finspace.replay import ReplayLedger, build_execution_identity, build_object_identity
from finspace.templates import european_option_space, fix_order_space, iso20022_payment_space


def test_fix_market_order_rejects_inactive_price() -> None:
    space = fix_order_space()
    market = next(record for record in space.enumerate() if record["order_type"] == "1")
    with pytest.raises(RecordValidationError):
        space.rank({**market, "price": 100.0})


def test_iso_pain_record_rejects_pacs_only_priority() -> None:
    space = iso20022_payment_space()
    pain = next(
        record for record in space.enumerate() if record["message"] == "pain.001.001.13"
    )
    with pytest.raises(RecordValidationError):
        space.rank({**pain, "priority": "HIGH"})


def test_iso_adapter_rejects_unsupported_message() -> None:
    pytest.importorskip("lxml")
    with pytest.raises(ValueError, match="unsupported ISO 20022 message"):
        ISO20022PaymentBuilder()({"message": "unsupported"})


def test_quantlib_adapter_rejects_unsupported_engine() -> None:
    pytest.importorskip("QuantLib")
    space = european_option_space(
        currencies=("USD",),
        spots=(100.0,),
        strikes=(100.0,),
        maturities_days=(30,),
        volatilities=(0.2,),
        dividends=(0.0,),
        rates_by_currency={"USD": (0.03,)},
    )
    record = {**space.unrank(0), "engine": "unsupported"}
    with pytest.raises(ValueError, match="unsupported QuantLib engine"):
        QuantLibEuropeanOptionPricer()(record)


def test_replay_verifier_distinguishes_each_mismatch_class() -> None:
    space = Space(Schema.from_dict({"name": "replay-negative", "fields": [{"name": "x", "values": [1, 2]}]}))
    environment = {"python": "3.12", "calendar": "NullCalendar"}
    oracle = {"name": "reference", "tolerance": 0.0}
    parameters = {"workers": 1}
    result = {"value": 1.0}

    with tempfile.TemporaryDirectory() as directory:
        with ReplayLedger(Path(directory) / "ledger.sqlite") as ledger:
            object_hash = ledger.record_object(build_object_identity(space, 0), space.unrank(0))
            identity = build_execution_identity(
                object_hash,
                adapter_name="reference",
                adapter_version="1",
                environment=environment,
                oracle_config=oracle,
                execution_parameters=parameters,
                external_data_snapshot="sha256:data-v1",
            )
            execution_hash = ledger.record_execution(
                identity,
                environment=environment,
                oracle_config=oracle,
                execution_parameters=parameters,
                result=result,
            )

            common = {
                "identity_hash": execution_hash,
                "adapter_name": "reference",
                "adapter_version": "1",
                "environment": environment,
                "oracle_config": oracle,
                "execution_parameters": parameters,
                "external_data_snapshot": "sha256:data-v1",
            }
            assert ledger.verify_execution(**common, observed_result=result) == "reproduced"
            assert ledger.verify_execution(**{**common, "adapter_version": "2"}) == "adapter-mismatch"
            assert ledger.verify_execution(
                **{**common, "environment": {**environment, "calendar": "TARGET"}}
            ) == "environment-mismatch"
            assert ledger.verify_execution(
                **{**common, "oracle_config": {"name": "reference", "tolerance": 1e-6}}
            ) == "oracle-mismatch"
            assert ledger.verify_execution(
                **{**common, "execution_parameters": {"workers": 2}}
            ) == "execution-parameters-mismatch"
            assert ledger.verify_execution(
                **{**common, "external_data_snapshot": None}
            ) == "external-data-unavailable"
            assert ledger.verify_execution(
                **common, observed_result={"value": 2.0}
            ) == "result-divergence"
