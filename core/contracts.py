"""Shared data contracts for the deterministic analytics core."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

SourceType = Literal[
    "csv",
    "excel",
    "database",
    "shopify",
    "market_api",
    "manual",
    "unknown",
]

ChartType = Literal["line", "bar", "histogram"]


@dataclass(frozen=True)
class DatasetInput:
    """Standard input contract every connector must return."""

    dataframe: pd.DataFrame
    source_type: SourceType
    value_column: str
    date_column: str | None = None
    category_column: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetProfile:
    """Data-quality and shape details computed before analysis."""

    source_type: SourceType
    original_row_count: int
    usable_numeric_row_count: int
    dropped_numeric_row_count: int
    duplicate_row_count: int
    missing_value_count: int
    numeric_columns: list[str]
    date_columns: list[str]
    categorical_columns: list[str]
    warnings: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Container for everything charts and the AI insight layer need."""

    dataset: DatasetInput
    profile: DatasetProfile
    row_count: int
    mean: float
    median: float
    mode: float | None
    std_dev: float
    variance: float
    min_value: float
    max_value: float
    total: float
    growth_rate_pct: float | None
    growth_rate_defined: bool
    avg_period_change_pct: float | None
    volatility: float | None
    anomalies: pd.DataFrame
    frequency_table: pd.Series
    recommended_chart_type: ChartType
    cleaned_df: pd.DataFrame = field(repr=False)
