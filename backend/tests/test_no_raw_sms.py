"""Compliance test verifying that NO raw SMS text is persisted in the database or logs."""

import logging

import pytest
from app.db.base import Base
from app.parsers.sms import parse_sms, parse_sms_batch


def test_no_raw_sms_table_or_column() -> None:
    """Verify that no database table or column stores raw SMS communications."""
    tables = Base.metadata.tables

    # 1. Ensure no table named sms or raw_sms exists
    forbidden_tables = {"sms", "raw_sms", "messages", "raw_messages", "sms_messages"}
    for tbl_name in tables:
        assert tbl_name.lower() not in forbidden_tables, (
            f"Forbidden communication table detected: {tbl_name}"
        )

    # 2. Inspect every column of every table
    forbidden_columns = {
        "sms",
        "raw_sms",
        "sms_body",
        "sms_text",
        "message_body",
        "message_text",
        "raw_text",
        "raw_message",
    }
    for tbl_name, table in tables.items():
        for col in table.columns:
            col_name = col.name.lower()
            assert col_name not in forbidden_columns, (
                f"Table '{tbl_name}' contains forbidden raw SMS column '{col.name}'"
            )

    # 3. Explicit check on feature_snapshots
    snapshots_cols = [c.name for c in tables["feature_snapshots"].columns]
    assert "features" in snapshots_cols
    assert "source_summary" in snapshots_cols
    assert "raw_sms" not in snapshots_cols


def test_no_raw_sms_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that processing SMS never writes the raw SMS body into application logs."""
    canary_text = (
        "CONFIDENTIAL_SECRET_CANARY_98765: Payment Tk 7,500.00 to ULTRA_SECRET_MERCHANT. "
        "User personal note: highly private details. TrxID SEC998877 on 15/11/2026."
    )

    with caplog.at_level(logging.DEBUG):
        trx = parse_sms(canary_text, use_llm_fallback=True)
        assert trx.amount_bdt == 7500.0
        _ = parse_sms_batch([canary_text, canary_text], use_llm_fallback=True)

    # Check all captured log entries
    for record in caplog.records:
        assert canary_text not in record.message, "Raw SMS body found in log records!"
        assert "CONFIDENTIAL_SECRET_CANARY_98765" not in record.message
        assert "ULTRA_SECRET_MERCHANT" not in record.message
        assert "highly private details" not in record.message
