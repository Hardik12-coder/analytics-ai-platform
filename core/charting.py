"""Deterministic chart selection and chart payload generation."""

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


def generate_chart_payload(
    result: AnalysisResult,
    chart_type: ChartType | str = "auto",
) -> dict:
    """Return frontend-ready Plotly-compatible JSON without requiring Plotly.

    The backend can return this directly. A frontend can render it with Plotly,
    and tests can validate it without importing the Plotly Python package.
    """

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

        traces = [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": value_column,
                "x": _serializable_list(df[date_column]),
                "y": _serializable_list(df[value_column]),
            }
        ]
        if not result.anomalies.empty:
            traces.append(
                {
                    "type": "scatter",
                    "mode": "markers",
                    "name": "Anomalies",
                    "x": _serializable_list(result.anomalies[date_column]),
                    "y": _serializable_list(result.anomalies[value_column]),
                    "marker": {"size": 11, "color": "#d62728", "symbol": "diamond"},
                }
            )

        return {
            "chart_type": "line",
            "figure": {
                "data": traces,
                "layout": {
                    "title": f"{value_column} over time",
                    "xaxis": {"title": date_column},
                    "yaxis": {"title": value_column},
                },
            },
        }

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

        return {
            "chart_type": "bar",
            "figure": {
                "data": [
                    {
                        "type": "bar",
                        "name": value_column,
                        "x": _serializable_list(x_values),
                        "y": _serializable_list(y_values),
                        "marker": {"color": "#2563eb"},
                    }
                ],
                "layout": {
                    "title": f"{value_column} by {x_title}",
                    "xaxis": {"title": x_title},
                    "yaxis": {"title": value_column},
                },
            },
        }

    return {
        "chart_type": "histogram",
        "figure": {
            "data": [
                {
                    "type": "histogram",
                    "name": value_column,
                    "x": _serializable_list(df[value_column]),
                    "marker": {"color": "#16a34a"},
                }
            ],
            "layout": {
                "title": f"{value_column} distribution",
                "xaxis": {"title": value_column},
                "yaxis": {"title": "Frequency"},
            },
        },
    }


def _validate_chart_type(chart_type: str) -> ChartType:
    if chart_type in {"line", "bar", "histogram"}:
        return chart_type  # type: ignore[return-value]
    raise ValueError("chart_type must be one of: auto, line, bar, histogram")


def _serializable_list(series: pd.Series) -> list:
    values = []
    for value in series.tolist():
        if pd.isna(value):
            values.append(None)
        elif hasattr(value, "isoformat"):
            values.append(value.isoformat())
        else:
            values.append(value.item() if hasattr(value, "item") else value)
    return values
