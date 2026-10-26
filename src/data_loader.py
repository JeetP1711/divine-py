import pandas as pd
import io
from typing import Tuple, List

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

COLUMN_ALIASES = {
    # Add common variations here if needed, e.g., "orderid": "order_id"
}

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to lower snake_case using REQUIRED_COLUMNS mapping.
    """
    df = df.copy()
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    # Apply aliases
    for alias, standard in COLUMN_ALIASES.items():
        if alias in df.columns:
            df.rename(columns={alias: standard}, inplace=True)
    return df

def validate_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validate required schema, types and basic data quality.
    Returns cleaned DataFrame and list of warning/error messages.
    """
    messages: List[str] = []
    # Check required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse dates
    try:
        df["date"] = pd.to_datetime(df["date"], errors="raise").dt.date
    except Exception as e:
        raise ValueError(f"Invalid date values: {e}")

    # Convert numeric columns
    numeric_cols = [
        "units",
        "selling_price",
        "unit_cost",
        "platform_fee",
        "shipping_cost",
        "ad_cost",
        "refund_amount",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isnull().any():
            messages.append(f"Column '{col}' contains non‑numeric values which were set to NaN.")
        if (df[col] < 0).any():
            messages.append(f"Column '{col}' contains negative values.")

    # Detect duplicate rows
    dup_mask = df.duplicated()
    if dup_mask.any():
        dup_count = dup_mask.sum()
        messages.append(f"Found {dup_count} duplicate rows.")

    # Detect rows with missing critical values
    if df[REQUIRED_COLUMNS].isnull().any().any():
        messages.append("Some required fields contain missing values.")

    return df, messages

def load_data(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, List[str]]:
    """Load CSV or Excel file from in‑memory bytes.
    Returns cleaned DataFrame and validation messages.
    """
    ext = filename.split(".")[-1].lower()
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif ext in {"xlsx", "xlsm", "xls"}:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Use CSV or Excel (xlsx, xlsm, xls).")

    df = normalize_column_names(df)
    df, messages = validate_dataframe(df)
    return df, messages
