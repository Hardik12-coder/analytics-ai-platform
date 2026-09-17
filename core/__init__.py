"""Core deterministic analytics package."""

from core.contracts import AnalysisResult, DatasetInput, DatasetProfile
from core.core_engine import analyze_dataframe, analyze_dataset, summarize_as_dict
from core.sales_engine import analyze_sales_dataframe

__all__ = [
    "AnalysisResult",
    "DatasetInput",
    "DatasetProfile",
    "analyze_dataframe",
    "analyze_dataset",
    "analyze_sales_dataframe",
    "summarize_as_dict",
]
