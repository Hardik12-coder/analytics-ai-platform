"""Deterministic sales/business metrics.

This module computes business facts that an LLM may later explain, but never
calculate. It is intentionally independent from file uploads and web APIs.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.ingestion import clean_dataframe, coerce_numeric


def analyze_sales_dataframe(
    df: pd.DataFrame,
    revenue_column: str,
    date_column: str | None = None,
    profit_column: str | None = None,
    units_column: str | None = None,
    category_column: str | None = None,
) -> dict[str, Any]:
    """Compute deterministic sales metrics from a cleaned or raw DataFrame."""

    sales_df = clean_dataframe(df)
    _require_column(sales_df, revenue_column, "revenue_column")

    sales_df[revenue_column] = coerce_numeric(sales_df[revenue_column])
    sales_df = sales_df[sales_df[revenue_column].notna()].copy()
    if sales_df.empty:
        raise ValueError(f"Column '{revenue_column}' has no usable revenue data.")

    if profit_column:
        _require_column(sales_df, profit_column, "profit_column")
        sales_df[profit_column] = coerce_numeric(sales_df[profit_column])
    if units_column:
        _require_column(sales_df, units_column, "units_column")
        sales_df[units_column] = coerce_numeric(sales_df[units_column])
    if date_column:
        _require_column(sales_df, date_column, "date_column")
        sales_df[date_column] = pd.to_datetime(sales_df[date_column], errors="coerce")
    if category_column:
        _require_column(sales_df, category_column, "category_column")

    total_revenue = float(sales_df[revenue_column].sum())
    total_profit = _sum_optional(sales_df, profit_column)
    total_units_sold = _sum_optional(sales_df, units_column)

    monthly_metrics = _monthly_metrics(
        sales_df,
        revenue_column=revenue_column,
        date_column=date_column,
        profit_column=profit_column,
        units_column=units_column,
    )
    category_metrics = _category_metrics(
        sales_df,
        revenue_column=revenue_column,
        category_column=category_column,
        profit_column=profit_column,
        units_column=units_column,
    )

    result = {
        "revenue_column": revenue_column,
        "profit_column": profit_column,
        "units_column": units_column,
        "date_column": date_column,
        "category_column": category_column,
        "transaction_count": int(len(sales_df)),
        "total_revenue": _round(total_revenue),
        "average_revenue_per_transaction": _round(sales_df[revenue_column].mean()),
        "median_revenue_per_transaction": _round(sales_df[revenue_column].median()),
        "total_profit": _round(total_profit),
        "profit_margin_pct": _pct(total_profit, total_revenue),
        "total_units_sold": _round(total_units_sold),
        "average_units_per_transaction": _round(
            sales_df[units_column].mean() if units_column else None
        ),
        "monthly_summary": _monthly_summary(monthly_metrics),
        "monthly_metrics": monthly_metrics,
        "category_metrics": category_metrics,
    }
    result["deterministic_findings"] = _deterministic_findings(result)
    return result


def _monthly_metrics(
    df: pd.DataFrame,
    revenue_column: str,
    date_column: str | None,
    profit_column: str | None,
    units_column: str | None,
) -> list[dict[str, Any]]:
    if not date_column:
        return []

    usable = df[df[date_column].notna()].copy()
    if usable.empty:
        return []

    usable["month"] = usable[date_column].dt.to_period("M").astype(str)
    grouped = usable.groupby("month", sort=True)
    rows: list[dict[str, Any]] = []
    previous_revenue: float | None = None

    for month, month_df in grouped:
        revenue = float(month_df[revenue_column].sum())
        profit = _sum_optional(month_df, profit_column)
        units = _sum_optional(month_df, units_column)
        row = {
            "month": month,
            "transaction_count": int(len(month_df)),
            "revenue": _round(revenue),
            "profit": _round(profit),
            "profit_margin_pct": _pct(profit, revenue),
            "units_sold": _round(units),
            "average_revenue_per_transaction": _round(month_df[revenue_column].mean()),
            "revenue_mom_growth_pct": _pct(
                revenue - previous_revenue, previous_revenue
            )
            if previous_revenue not in (None, 0)
            else None,
        }
        rows.append(row)
        previous_revenue = revenue

    return rows


def _monthly_summary(monthly_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not monthly_metrics:
        return {
            "month_count": 0,
            "average_monthly_revenue": None,
            "median_monthly_revenue": None,
            "best_month_by_revenue": None,
            "worst_month_by_revenue": None,
            "first_to_last_month_growth_pct": None,
        }

    revenue_series = pd.Series([row["revenue"] for row in monthly_metrics], dtype="float64")
    best_month = max(monthly_metrics, key=lambda row: row["revenue"])
    worst_month = min(monthly_metrics, key=lambda row: row["revenue"])
    first_revenue = monthly_metrics[0]["revenue"]
    last_revenue = monthly_metrics[-1]["revenue"]

    return {
        "month_count": len(monthly_metrics),
        "average_monthly_revenue": _round(revenue_series.mean()),
        "median_monthly_revenue": _round(revenue_series.median()),
        "best_month_by_revenue": {
            "month": best_month["month"],
            "revenue": best_month["revenue"],
        },
        "worst_month_by_revenue": {
            "month": worst_month["month"],
            "revenue": worst_month["revenue"],
        },
        "first_to_last_month_growth_pct": _pct(last_revenue - first_revenue, first_revenue),
    }


def _category_metrics(
    df: pd.DataFrame,
    revenue_column: str,
    category_column: str | None,
    profit_column: str | None,
    units_column: str | None,
) -> list[dict[str, Any]]:
    if not category_column:
        return []

    rows = []
    grouped = df.groupby(category_column, dropna=False, sort=True)
    for category, category_df in grouped:
        revenue = float(category_df[revenue_column].sum())
        profit = _sum_optional(category_df, profit_column)
        units = _sum_optional(category_df, units_column)
        rows.append(
            {
                "category": str(category),
                "transaction_count": int(len(category_df)),
                "revenue": _round(revenue),
                "profit": _round(profit),
                "profit_margin_pct": _pct(profit, revenue),
                "units_sold": _round(units),
            }
        )

    return sorted(rows, key=lambda row: row["revenue"], reverse=True)


def _deterministic_findings(result: dict[str, Any]) -> list[str]:
    findings = [
        f"Total revenue is {result['total_revenue']} across {result['transaction_count']} transactions.",
    ]

    if result["profit_margin_pct"] is not None:
        findings.append(f"Overall profit margin is {result['profit_margin_pct']}%.")

    monthly_summary = result["monthly_summary"]
    growth = monthly_summary.get("first_to_last_month_growth_pct")
    if growth is not None:
        direction = "increased" if growth > 0 else "decreased" if growth < 0 else "stayed flat"
        findings.append(f"Monthly revenue {direction} by {abs(growth)}% from first to last month.")

    if result["category_metrics"]:
        top = result["category_metrics"][0]
        findings.append(
            f"Top category by revenue is {top['category']} with {top['revenue']} revenue."
        )

    return findings


def _require_column(df: pd.DataFrame, column: str, argument_name: str) -> None:
    if column not in df.columns:
        raise ValueError(
            f"{argument_name} '{column}' not found. Available columns: {list(df.columns)}"
        )


def _sum_optional(df: pd.DataFrame, column: str | None) -> float | None:
    if not column:
        return None
    series = df[column].dropna()
    if series.empty:
        return None
    return float(series.sum())


def _pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return _round((numerator / denominator) * 100)


def _round(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 2)
