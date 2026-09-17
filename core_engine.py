"""
core_engine.py

The statistical core of the Analytics AI platform.

Design principle: this module is the SOURCE OF TRUTH for all numbers.
The LLM layer (separate module, added later) is only allowed to
INTERPRET the output of this file in plain English - it never
calculates anything itself. This keeps the numbers trustworthy
regardless of which language model you plug in later.

Usage:
    from core_engine import analyze_dataset
    result = analyze_dataset("sales_data.csv", value_column="Revenue", date_column="Date")
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnalysisResult:
    """Container for everything the AI insight layer will need later."""
    row_count: int
    mean: float
    median: float
    mode: Optional[float]
    std_dev: float
    variance: float
    min_value: float
    max_value: float
    total: float
    growth_rate_pct: float          # overall change from first to last value
    avg_period_change_pct: float    # average period-over-period % change
    volatility: float               # std dev of the period-over-period % changes
    anomalies: pd.DataFrame          # rows flagged as statistical outliers
    frequency_table: pd.Series       # value distribution (useful for categorical/bucketed data)
    cleaned_df: pd.DataFrame = field(repr=False)  # the parsed data, for chart-building later


def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Loads a CSV (or Excel) file into a DataFrame and does basic cleanup:
    - drops fully empty rows
    - strips whitespace from column names
    - attempts to parse any obvious date columns
    """
    if filepath.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath)

    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(how="all")

    for col in df.columns:
        if "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except (ValueError, TypeError):
                pass

    return df


def analyze_dataset(
    filepath: str,
    value_column: str,
    date_column: Optional[str] = None,
    z_score_threshold: float = 2.0,
) -> AnalysisResult:
    """
    Runs the full statistical analysis on one numeric column of a dataset.

    Args:
        filepath: path to the CSV/Excel file
        value_column: the numeric column to analyze (e.g. "Revenue", "UnitsSold", "ClosePrice")
        date_column: optional column to sort by chronologically (e.g. "Date")
        z_score_threshold: how many standard deviations from the mean counts as an anomaly

    Returns:
        AnalysisResult with every statistic the insight layer and chart layer need.
    """
    df = load_dataset(filepath)

    if value_column not in df.columns:
        raise ValueError(f"Column '{value_column}' not found. Available columns: {list(df.columns)}")

    if date_column and date_column in df.columns:
        df = df.sort_values(by=date_column).reset_index(drop=True)

    series = pd.to_numeric(df[value_column], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"Column '{value_column}' has no usable numeric data.")

    mean = float(series.mean())
    median = float(series.median())
    mode_vals = series.mode()
    mode = float(mode_vals.iloc[0]) if not mode_vals.empty else None
    std_dev = float(series.std())
    variance = float(series.var())

    # Period-over-period % change (e.g. day-over-day, week-over-week)
    pct_change = series.pct_change().dropna() * 100
    avg_period_change_pct = float(pct_change.mean()) if not pct_change.empty else 0.0
    volatility = float(pct_change.std()) if not pct_change.empty else 0.0

    growth_rate_pct = (
        float(((series.iloc[-1] - series.iloc[0]) / series.iloc[0]) * 100)
        if series.iloc[0] != 0 else 0.0
    )

    # Anomaly detection via z-score
    z_scores = (series - mean) / std_dev if std_dev != 0 else series * 0
    df_with_z = df.loc[series.index].copy()
    df_with_z["z_score"] = z_scores
    df_with_z["pct_change"] = pct_change.reindex(df_with_z.index)
    anomalies = df_with_z[df_with_z["z_score"].abs() > z_score_threshold]

    # Frequency distribution - useful when the column is categorical or bucketed
    frequency_table = series.value_counts().sort_index()

    return AnalysisResult(
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
        avg_period_change_pct=avg_period_change_pct,
        volatility=volatility,
        anomalies=anomalies,
        frequency_table=frequency_table,
        cleaned_df=df_with_z,
    )


def summarize_as_dict(result: AnalysisResult) -> dict:
    """
    Converts the AnalysisResult into a plain dict of primitives only
    (no DataFrames). This is what you hand to the LLM insight layer -
    it should only ever see numbers, never raw data or code.
    """
    return {
        "row_count": result.row_count,
        "mean": round(result.mean, 2),
        "median": round(result.median, 2),
        "mode": round(result.mode, 2) if result.mode is not None else None,
        "std_dev": round(result.std_dev, 2),
        "variance": round(result.variance, 2),
        "min_value": round(result.min_value, 2),
        "max_value": round(result.max_value, 2),
        "total": round(result.total, 2),
        "growth_rate_pct": round(result.growth_rate_pct, 2),
        "avg_period_change_pct": round(result.avg_period_change_pct, 2),
        "volatility": round(result.volatility, 2),
        "anomaly_count": len(result.anomalies),
    }


if __name__ == "__main__":
    # Quick manual test - replace with a real CSV path to try it out
    import sys

    if len(sys.argv) < 3:
        print("Usage: python core_engine.py <path_to_csv> <value_column> [date_column]")
        sys.exit(1)

    path = sys.argv[1]
    value_col = sys.argv[2]
    date_col = sys.argv[3] if len(sys.argv) > 3 else None

    result = analyze_dataset(path, value_col, date_col)
    print("\n--- STATISTICAL SUMMARY ---")
    for k, v in summarize_as_dict(result).items():
        print(f"{k}: {v}")

    if not result.anomalies.empty:
        print(f"\n--- {len(result.anomalies)} ANOMALIES DETECTED ---")
        print(result.anomalies)
