"""In-memory loading and validation for normalized sales reports."""

import io
import re
import zipfile
from typing import List, Tuple

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

REQUIRED_COLUMNS = [
    "date",
    "order_id",
    "marketplace",
    "sku",
    "product_name",
    "units",
    "selling_price",
    "unit_cost",
    "platform_fee",
    "shipping_cost",
    "ad_cost",
    "refund_amount",
]
NUMERIC_COLUMNS = [
    "units",
    "selling_price",
    "unit_cost",
    "platform_fee",
    "shipping_cost",
    "ad_cost",
    "refund_amount",
]
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Kept separate so marketplace-specific aliases can be added without changing validation.
COLUMN_ALIASES = {}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize header case and separators into snake_case."""
    normalized = df.copy()
    normalized.columns = [
        re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower())).strip("_")
        for column in normalized.columns
    ]
    normalized.rename(columns=COLUMN_ALIASES, inplace=True)
    duplicate_columns = normalized.columns[normalized.columns.duplicated()].tolist()
    if duplicate_columns:
        raise ValueError(
            "Multiple input columns normalize to the same name: "
            + ", ".join(sorted(set(duplicate_columns)))
        )
    return normalized


def validate_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validate required schema and values without dropping or imputing records."""
    if df.empty:
        raise ValueError("The file contains no sales rows. Add data below the header and try again.")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
            + ". Download the CSV template to check the expected schema."
        )

    result = df[REQUIRED_COLUMNS].copy()
    issues = []

    for column in ("order_id", "marketplace", "sku", "product_name"):
        result[column] = result[column].astype("string").str.strip()
        missing = result[column].isna() | result[column].eq("")
        if missing.any():
            rows = (result.index[missing] + 2).tolist()[:5]
            issues.append(f"'{column}' is blank on spreadsheet row(s): {rows}.")

    parsed_dates = pd.to_datetime(result["date"], errors="coerce")
    bad_dates = parsed_dates.isna()
    if bad_dates.any():
        rows = (result.index[bad_dates] + 2).tolist()[:5]
        issues.append(f"'date' has missing or invalid values on spreadsheet row(s): {rows}.")
    result["date"] = parsed_dates.dt.date

    for column in NUMERIC_COLUMNS:
        source = result[column]
        converted = pd.to_numeric(source, errors="coerce")
        invalid = converted.isna() & source.notna() & source.astype("string").str.strip().ne("")
        missing = converted.isna() & ~invalid
        if invalid.any():
            rows = (result.index[invalid] + 2).tolist()[:5]
            issues.append(
                f"'{column}' contains non-numeric values on spreadsheet row(s): {rows}."
            )
        if missing.any():
            rows = (result.index[missing] + 2).tolist()[:5]
            issues.append(f"'{column}' is missing on spreadsheet row(s): {rows}.")
        non_finite = converted.isin([float("inf"), float("-inf")])
        if non_finite.any():
            rows = (result.index[non_finite] + 2).tolist()[:5]
            issues.append(f"'{column}' must contain finite numbers (spreadsheet row(s): {rows}).")
        result[column] = converted

    negative_columns = [
        column for column in NUMERIC_COLUMNS
        if result[column].lt(0).fillna(False).any()
    ]
    for column in negative_columns:
        rows = (result.index[result[column].lt(0).fillna(False)] + 2).tolist()[:5]
        issues.append(f"'{column}' cannot be negative (spreadsheet row(s): {rows}).")

    zero_units = result["units"].eq(0).fillna(False)
    if zero_units.any():
        rows = (result.index[zero_units] + 2).tolist()[:5]
        issues.append(f"'units' must be greater than zero (spreadsheet row(s): {rows}).")

    if issues:
        raise ValueError("Please correct the following data issues; no rows were discarded:\n- " + "\n- ".join(issues))

    messages = []
    duplicate_count = int(result.duplicated().sum())
    if duplicate_count:
        messages.append(
            f"Found {duplicate_count} duplicate row(s). Review the source to ensure they are intentional."
        )

    zero_cost = result["unit_cost"].eq(0)
    if zero_cost.any():
        messages.append(
            f"{int(zero_cost.sum())} row(s) have a unit cost of ₹0. Confirm that these costs are intentional."
        )
    return result, messages


def load_data(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, List[str]]:
    """Load a CSV/XLSX/XLSM report from bytes and return validated rows and warnings."""
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("The file exceeds the 50 MB upload limit.")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in {"csv", "xlsx", "xlsm"}:
        raise ValueError("Unsupported file type. Use a CSV, XLSX, or XLSM file.")
    try:
        if extension == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes), keep_default_na=False)
        else:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The CSV file is empty or contains no header row.") from exc
    except (
        OSError,
        ValueError,
        ImportError,
        UnicodeDecodeError,
        pd.errors.ParserError,
        zipfile.BadZipFile,
        InvalidFileException,
    ) as exc:
        raise ValueError(f"Could not read '{filename}'. Check that it is a valid {extension.upper()} file.") from exc

    if df.empty and len(df.columns) == 0:
        raise ValueError("The file contains no header row or sales data.")
    return validate_dataframe(normalize_column_names(df))
