"""Deterministic chart selection and Plotly generation."""

from __future__ import annotations

import pandas as pd

from core.contracts import AnalysisResult, ChartType, DatasetInput


def recommend_chart_type(dataset: DatasetInput, series: pd.Series) -> ChartType:
    """Choose a chart type from data shape, without asking an LLM."""

    if dataset.date_column:
        return "line"
    if dataset.category_column:
        return "bar"

    unique_ratio = series.nunique(dropna=True) / max(len(series), 1)
    if unique_ratio < 0.25 and series.nunique(dropna=True) <= 25:
        return "bar"
    return "histogram"


def generate_chart(
    result: AnalysisResult,
    chart_type: ChartType | str = "auto",
) -> go.Figure:
    """Generate a Plotly chart and highlight z-score anomalies where relevant."""

    import plotly.graph_objects as go

    selected_chart = (
        result.recommended_chart_type if chart_type == "auto" else _validate_chart_type(chart_type)
    )
    df = result.cleaned_df
    value_column = result.dataset.value_column
    date_column = result.dataset.date_column
    category_column = result.dataset.category_column

    if selected_chart == "line":
        if not date_column:
            raise ValueError("A line chart requires a date_column.")

        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=df[date_column],
                y=df[value_column],
                mode="lines+markers",
                name=value_column,
            )
        )
        if not result.anomalies.empty:
            figure.add_trace(
                go.Scatter(
                    x=result.anomalies[date_column],
                    y=result.anomalies[value_column],
                    mode="markers",
                    name="Anomalies",
                    marker={"size": 11, "color": "#d62728", "symbol": "diamond"},
                )
            )
        figure.update_layout(xaxis_title=date_column, yaxis_title=value_column)
        return figure

    if selected_chart == "bar":
        if category_column:
            grouped = df.groupby(category_column, dropna=False)[value_column].sum().reset_index()
            x_values = grouped[category_column]
            y_values = grouped[value_column]
            x_title = category_column
        else:
            counts = df[value_column].value_counts().sort_index()
            x_values = counts.index.astype(str)
            y_values = counts.values
            x_title = value_column

        figure = go.Figure(
            data=[
                go.Bar(
                    x=x_values,
                    y=y_values,
                    name=value_column,
                    marker={"color": "#2563eb"},
                )
            ]
        )
        figure.update_layout(xaxis_title=x_title, yaxis_title=value_column)
        return figure

    figure = go.Figure(
        data=[
            go.Histogram(
                x=df[value_column],
                name=value_column,
                marker={"color": "#16a34a"},
            )
        ]
    )
    figure.update_layout(xaxis_title=value_column, yaxis_title="Frequency")
    return figure


def _validate_chart_type(chart_type: str) -> ChartType:
    if chart_type in {"line", "bar", "histogram"}:
        return chart_type  # type: ignore[return-value]
    raise ValueError("chart_type must be one of: auto, line, bar, histogram")
