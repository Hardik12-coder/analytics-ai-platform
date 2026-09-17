"""Deterministic analysis pipeline used by the backend API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.charting import generate_chart_payload
from core.core_engine import analyze_dataframe, summarize_as_dict
from core.ingestion import load_dataset
from core.sales_engine import analyze_sales_dataframe


def run_deterministic_analysis_file(
    filepath: str | Path,
    value_column: str,
    date_column: str | None = None,
    category_column: str | None = None,
    profit_column: str | None = None,
    units_column: str | None = None,
    z_score_threshold: float = 3.0,
) -> dict[str, Any]:
    """Run the no-LLM analysis pipeline for one uploaded file."""

    dataset = load_dataset(
        filepath=filepath,
        value_column=value_column,
        date_column=date_column,
        category_column=category_column,
    )
    analysis = analyze_dataframe(dataset, z_score_threshold=z_score_threshold)
    stats = summarize_as_dict(analysis)
    chart = generate_chart_payload(analysis)
    sales_metrics = analyze_sales_dataframe(
        dataset.dataframe,
        revenue_column=dataset.value_column,
        date_column=dataset.date_column,
        profit_column=profit_column,
        units_column=units_column,
        category_column=dataset.category_column,
    )

    return {
        "status": "ok",
        "llm_enabled": False,
        "insight": None,
        "stats": stats,
        "sales_metrics": sales_metrics,
        "chart": chart,
    }
