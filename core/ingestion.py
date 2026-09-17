"""Data loading and profiling helpers.

CSV/Excel loading lives here as one connector path. Future database, Shopify,
and market-data connectors should return DatasetInput objects and reuse the
same core engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.contracts import DatasetInput, DatasetProfile, SourceType


def load_dataset(
    filepath: str | Path,
    value_column: str,
    date_column: str | None = None,
    category_column: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> DatasetInput:
    """Load a CSV/Excel file into the standard DatasetInput contract."""

    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
        source_type: SourceType = "excel"
    elif suffix == ".csv":
        df = pd.read_csv(path)
        source_type = "csv"
    else:
        raise ValueError(f"Unsupported dataset file type: {suffix or '<none>'}")

    df = clean_dataframe(df)
    resolved_value_column = _resolve_column(df, value_column)
    resolved_date_column = _resolve_column(df, date_column) if date_column else None
    resolved_category_column = _resolve_column(df, category_column) if category_column else None

    return DatasetInput(
        dataframe=df,
        source_type=source_type,
        value_column=resolved_value_column,
        date_column=resolved_date_column,
        category_column=resolved_category_column,
        metadata={"filename": path.name, **(metadata or {})},
    )


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply source-agnostic cleanup without changing business meaning."""

    cleaned = df.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    cleaned = cleaned.dropna(how="all").reset_index(drop=True)

    for column in cleaned.columns:
        if "date" in column.lower():
            parsed = pd.to_datetime(cleaned[column], errors="coerce")
            if parsed.notna().any():
                cleaned[column] = parsed

    return cleaned


def profile_dataset(dataset: DatasetInput, numeric_series: pd.Series) -> DatasetProfile:
    """Build a deterministic data profile for quality warnings and UI display."""

    df = dataset.dataframe
    warnings: list[str] = []
    original_row_count = len(df)
    usable_numeric_row_count = int(numeric_series.notna().sum())
    dropped_numeric_row_count = original_row_count - usable_numeric_row_count
    duplicate_row_count = int(df.duplicated().sum())
    missing_value_count = int(df.isna().sum().sum())

    numeric_columns = [
        column
        for column in df.columns
        if pd.to_numeric(_strip_number_formatting(df[column]), errors="coerce").notna().any()
    ]
    date_columns = [
        column for column in df.columns if pd.api.types.is_datetime64_any_dtype(df[column])
    ]
    categorical_columns = [
        column
        for column in df.columns
        if column not in numeric_columns and column not in date_columns
    ]

    if dropped_numeric_row_count:
        warnings.append(
            f"{dropped_numeric_row_count} rows were excluded because "
            f"'{dataset.value_column}' was missing or non-numeric."
        )
    if duplicate_row_count:
        warnings.append(f"{duplicate_row_count} duplicate rows were detected.")
    if dataset.date_column and dataset.date_column not in date_columns:
        warnings.append(f"'{dataset.date_column}' was not parsed as a reliable date column.")

    return DatasetProfile(
        source_type=dataset.source_type,
        original_row_count=original_row_count,
        usable_numeric_row_count=usable_numeric_row_count,
        dropped_numeric_row_count=dropped_numeric_row_count,
        duplicate_row_count=duplicate_row_count,
        missing_value_count=missing_value_count,
        numeric_columns=numeric_columns,
        date_columns=date_columns,
        categorical_columns=categorical_columns,
        warnings=warnings,
    )


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert common business-number strings into numeric values."""

    return pd.to_numeric(_strip_number_formatting(series), errors="coerce")


def _strip_number_formatting(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series

    return (
        series.astype("string")
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    )


def _resolve_column(df: pd.DataFrame, requested: str | None) -> str:
    if requested is None:
        raise ValueError("Column name is required.")
    if requested in df.columns:
        return requested

    normalized = {column.strip().lower(): column for column in df.columns}
    resolved = normalized.get(requested.strip().lower())
    if resolved:
        return resolved

    raise ValueError(f"Column '{requested}' not found. Available columns: {list(df.columns)}")
