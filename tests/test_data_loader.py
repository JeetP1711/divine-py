"""Tests for sales file parsing and validation."""

from io import BytesIO

import pandas as pd
import pytest

from src.data_loader import REQUIRED_COLUMNS, load_data, normalize_column_names, validate_dataframe


@pytest.fixture
def valid_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2026-01-02",
                "order_id": "ORDER-1",
                "marketplace": "Sample Shop",
                "sku": "SAMPLE-1",
                "product_name": "Fictional Garden Blend",
                "units": 2,
                "selling_price": 120,
                "unit_cost": 50,
                "platform_fee": 10,
                "shipping_cost": 5,
                "ad_cost": 3,
                "refund_amount": 0,
            }
        ]
    )


def test_normalize_column_names_handles_case_and_separators():
    frame = pd.DataFrame(columns=[" Order ID ", "Selling-Price"])
    assert normalize_column_names(frame).columns.tolist() == ["order_id", "selling_price"]


def test_missing_required_columns_are_reported(valid_rows):
    with pytest.raises(ValueError, match="Missing required columns:.*marketplace"):
        validate_dataframe(valid_rows.drop(columns=["marketplace"]))


def test_invalid_numeric_values_are_rejected_without_dropping_rows(valid_rows):
    valid_rows["unit_cost"] = ["not a cost"]
    with pytest.raises(ValueError, match="unit_cost.*non-numeric"):
        validate_dataframe(valid_rows)


def test_missing_required_values_are_rejected(valid_rows):
    valid_rows.loc[0, "refund_amount"] = None
    with pytest.raises(ValueError, match="refund_amount.*missing"):
        validate_dataframe(valid_rows)


@pytest.mark.parametrize("column", ["selling_price", "unit_cost", "platform_fee"])
def test_negative_price_or_cost_values_are_rejected(valid_rows, column):
    valid_rows.loc[0, column] = -1
    with pytest.raises(ValueError, match=f"{column}.*cannot be negative"):
        validate_dataframe(valid_rows)


def test_duplicate_rows_produce_a_warning(valid_rows):
    duplicated = pd.concat([valid_rows, valid_rows], ignore_index=True)
    _, warnings = validate_dataframe(duplicated)
    assert any("1 duplicate row" in warning for warning in warnings)


def test_empty_csv_has_a_friendly_error():
    with pytest.raises(ValueError, match="empty"):
        load_data(b"", "sales.csv")


def test_empty_csv_without_header_has_a_friendly_error():
    with pytest.raises(ValueError, match="empty or contains no header"):
        load_data(b"\n", "sales.csv")


def test_csv_loads_with_date_and_numeric_types(valid_rows):
    contents = valid_rows.to_csv(index=False).encode("utf-8")
    loaded, warnings = load_data(contents, "sales.csv")
    assert loaded.columns.tolist() == REQUIRED_COLUMNS
    assert loaded.loc[0, "units"] == 2
    assert str(loaded.loc[0, "date"]) == "2026-01-02"
    assert warnings == []


def test_xlsx_upload_is_parsed_in_memory(valid_rows):
    workbook = BytesIO()
    valid_rows.to_excel(workbook, index=False)
    loaded, _ = load_data(workbook.getvalue(), "sales.xlsx")
    assert loaded.loc[0, "sku"] == "SAMPLE-1"


def test_unsupported_file_type_is_rejected():
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_data(b"data", "sales.xls")


def test_zero_unit_cost_is_warned_instead_of_imputed(valid_rows):
    valid_rows.loc[0, "unit_cost"] = 0
    loaded, warnings = validate_dataframe(valid_rows)
    assert loaded.loc[0, "unit_cost"] == 0
    assert any("unit cost of ₹0" in warning for warning in warnings)
