"""Compliance test verifying that NO column in the database stores raw SMS text."""

from app.db.base import Base


def test_no_raw_sms_table_or_column() -> None:
    """Verify that no database table or column stores raw SMS communications."""
    # List of all tables in metadata
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
