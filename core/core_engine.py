"""Deterministic statistical core for the Analytics AI platform.

This module is the source of truth for all numbers. The LLM layer receives only
computed summaries from this module and is never responsible for calculations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.charting import recommend_chart_type
from core.contracts import AnalysisResult, DatasetInput
from core.ingestion import coerce_numeric, load_dataset, profile_dataset


def analyze_dataset(
    filepath: str | Path,
    value_column: str,
    date_column: str | None = None,
    category_column: str | None = None,
    z_score_threshold: float = 3.0,
) -> AnalysisResult:
    """Load a CSV/Excel file and analyze it through the common engine."""

    dataset = load_dataset(
        filepath=filepath,
        value_column=value_column,
        date_column=date_column,
        category_column=category_column,
    )
    return analyze_dataframe(dataset, z_score_threshold=z_score_threshold)


def analyze_dataframe(
    dataset: DatasetInput,
    z_score_threshold: float = 3.0,
) -> AnalysisResult:
    """Run deterministic statistical analysis on a DatasetInput object."""

    df = dataset.dataframe.copy()

    if dataset.value_column not in df.columns:
        raise ValueError(
            f"Column '{dataset.value_column}' not found. Available columns: {list(df.columns)}"
        )
    if dataset.date_column and dataset.date_column not in df.columns:
        raise ValueError(
            f"Date column '{dataset.date_column}' not found. Available columns: {list(df.columns)}"
        )
    if dataset.category_column and dataset.category_column not in df.columns:
        raise ValueError(
            f"Category column '{dataset.category_column}' not found. Available columns: {list(df.columns)}"
        )

    if dataset.date_column:
        df = df.sort_values(by=dataset.date_column).reset_index(drop=True)

    numeric_series = coerce_numeric(df[dataset.value_column])
    profile = profile_dataset(dataset, numeric_series)
    valid_mask = numeric_series.notna()

    series = numeric_series.loc[valid_mask].astype(float)
    if series.empty:
        raise ValueError(f"Column '{dataset.value_column}' has no usable numeric data.")

    cleaned_df = df.loc[valid_mask].copy()
    cleaned_df[dataset.value_column] = series

    mean = float(series.mean())
    median = float(series.median())
    mode = _meaningful_mode(series)
    std_dev = _finite_or_zero(series.std())
    variance = _finite_or_zero(series.var())
    pct_change = _period_percent_change(series)
    avg_period_change_pct = _finite_or_none(pct_change.mean()) if not pct_change.empty else None
    volatility = _finite_or_none(pct_change.std()) if len(pct_change) > 1 else None
    growth_rate_pct = _growth_rate(series)
    z_scores = _z_scores(series, mean, std_dev)

    cleaned_df["z_score"] = z_scores
    cleaned_df["pct_change"] = pct_change.reindex(cleaned_df.index)
    anomalies = cleaned_df[cleaned_df["z_score"].abs() > z_score_threshold]
    frequency_table = series.value_counts().sort_index()
    recommended_chart_type = recommend_chart_type(dataset, series)

    return AnalysisResult(
        dataset=dataset,
        profile=profile,
        row_count=len(series),
        mean=mean,
        median=median,
        mode=mode,
        std_dev=std_dev,
        variance=variance,
        min_value=float(series.min()),
        max_value=float(series.max()),
        total=float(series.sum()),
        growth_rate_pct=growth_rate_pct,
        growth_rate_defined=growth_rate_pct is not None,
        avg_period_change_pct=avg_period_change_pct,
        volatility=volatility,
        anomalies=anomalies,
        frequency_table=frequency_table,
        recommended_chart_type=recommended_chart_type,
        cleaned_df=cleaned_df,
    )


def summarize_as_dict(result: AnalysisResult) -> dict[str, Any]:
    """Convert AnalysisResult into the primitive-only payload for the LLM."""

    anomaly_examples = [
        {
            "row_index": int(index),
            "value": _round_or_none(row[result.dataset.value_column]),
            "z_score": _round_or_none(row["z_score"]),
            "pct_change": _round_or_none(row["pct_change"]),
        }
        for index, row in result.anomalies.head(5).iterrows()
    ]

    payload = {
        "source_type": result.dataset.source_type,
        "value_column": result.dataset.value_column,
        "date_column": result.dataset.date_column,
        "category_column": result.dataset.category_column,
        "row_count": result.row_count,
        "mean": round(result.mean, 2),
        "median": round(result.median, 2),
        "mode": _round_or_none(result.mode),
        "std_dev": round(result.std_dev, 2),
        "variance": round(result.variance, 2),
        "min_value": round(result.min_value, 2),
        "max_value": round(result.max_value, 2),
        "total": round(result.total, 2),
        "growth_rate_pct": _round_or_none(result.growth_rate_pct),
        "growth_rate_defined": result.growth_rate_defined,
        "avg_period_change_pct": _round_or_none(result.avg_period_change_pct),
        "volatility": _round_or_none(result.volatility),
        "anomaly_count": len(result.anomalies),
        "anomaly_examples": anomaly_examples,
        "recommended_chart_type": result.recommended_chart_type,
        "data_quality": {
            "original_row_count": result.profile.original_row_count,
            "usable_numeric_row_count": result.profile.usable_numeric_row_count,
            "dropped_numeric_row_count": result.profile.dropped_numeric_row_count,
            "duplicate_row_count": result.profile.duplicate_row_count,
            "missing_value_count": result.profile.missing_value_count,
            "warnings": result.profile.warnings,
        },
    }

    return payload


def _meaningful_mode(series: pd.Series) -> float | None:
    counts = series.value_counts()
    if counts.empty or counts.iloc[0] < 2:
        return None
    return float(counts.index[0])


def _period_percent_change(series: pd.Series) -> pd.Series:
    pct_change = series.pct_change(fill_method=None) * 100
    return pct_change.replace([np.inf, -np.inf], np.nan).dropna()


def _growth_rate(series: pd.Series) -> float | None:
    first = series.iloc[0]
    last = series.iloc[-1]
    if first == 0:
        return None
    return float(((last - first) / first) * 100)


def _z_scores(series: pd.Series, mean: float, std_dev: float) -> pd.Series:
    if std_dev == 0:
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std_dev


def _finite_or_zero(value: float) -> float:
    return float(value) if pd.notna(value) and np.isfinite(value) else 0.0


def _finite_or_none(value: float) -> float | None:
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def _round_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m core.core_engine <path_to_csv> <value_column> [date_column]")
        raise SystemExit(1)

    path = sys.argv[1]
    value_col = sys.argv[2]
    date_col = sys.argv[3] if len(sys.argv) > 3 else None

    analysis = analyze_dataset(path, value_col, date_col)
    print("\n--- STATISTICAL SUMMARY ---")
    for key, value in summarize_as_dict(analysis).items():
        print(f"{key}: {value}")

    if not analysis.anomalies.empty:
        print(f"\n--- {len(analysis.anomalies)} ANOMALIES DETECTED ---")
        print(analysis.anomalies)
