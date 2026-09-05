"""Core deterministic analytics package."""

from core.contracts import AnalysisResult, DatasetInput, DatasetProfile
from core.core_engine import analyze_dataframe, analyze_dataset, summarize_as_dict

__all__ = [
    "AnalysisResult",
    "DatasetInput",
    "DatasetProfile",
    "analyze_dataframe",
    "analyze_dataset",
    "summarize_as_dict",
]
