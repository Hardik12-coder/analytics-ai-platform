import math

import pandas as pd

from core import DatasetInput, analyze_dataframe, analyze_dataset, summarize_as_dict


def test_analyze_dataset_computes_basic_stats_from_csv():
    result = analyze_dataset(
        "tests/fixtures/sample_sales.csv",
        value_column="Revenue",
        date_column="Date",
        category_column="Product",
        z_score_threshold=2.0,
    )

    assert result.row_count == 10
    assert result.mean == 1736.0
    assert result.median == 1375.0
    assert result.mode is None
    assert result.min_value == 1200.0
    assert result.max_value == 5200.0
    assert result.total == 17360.0
    assert result.growth_rate_pct == 25.0
    assert result.recommended_chart_type == "line"
    assert len(result.anomalies) == 1


def test_analyze_dataframe_is_source_agnostic():
    df = pd.DataFrame(
        {
            "period": ["2026-01", "2026-02", "2026-03"],
            "revenue": ["$1,000", "$1,500", "$2,000"],
        }
    )
    dataset = DatasetInput(
        dataframe=df,
        source_type="database",
        value_column="revenue",
        date_column="period",
    )

    result = analyze_dataframe(dataset)

    assert result.row_count == 3
    assert result.mean == 1500.0
    assert result.total == 4500.0
    assert result.growth_rate_pct == 100.0
    assert result.profile.source_type == "database"


def test_growth_rate_is_undefined_when_first_value_is_zero():
    dataset = DatasetInput(
        dataframe=pd.DataFrame({"revenue": [0, 100, 200]}),
        source_type="manual",
        value_column="revenue",
    )

    result = analyze_dataframe(dataset)
    summary = summarize_as_dict(result)

    assert result.growth_rate_pct is None
    assert summary["growth_rate_defined"] is False


def test_single_row_dataset_has_stable_variance_and_volatility():
    dataset = DatasetInput(
        dataframe=pd.DataFrame({"revenue": [100]}),
        source_type="manual",
        value_column="revenue",
    )

    result = analyze_dataframe(dataset)

    assert result.std_dev == 0.0
    assert result.variance == 0.0
    assert result.avg_period_change_pct is None
    assert result.volatility is None
    assert result.anomalies.empty


def test_summary_payload_contains_only_llm_safe_context():
    result = analyze_dataset(
        "tests/fixtures/sample_sales.csv",
        value_column="Revenue",
        date_column="Date",
        category_column="Product",
        z_score_threshold=2.0,
    )

    payload = summarize_as_dict(result)

    assert payload["value_column"] == "Revenue"
    assert payload["source_type"] == "csv"
    assert payload["recommended_chart_type"] == "line"
    assert payload["anomaly_count"] == 1
    assert "warnings" in payload["data_quality"]
    assert not any(isinstance(value, pd.DataFrame) for value in payload.values())
    assert not any(isinstance(value, pd.Series) for value in payload.values())


def test_repeated_values_have_a_meaningful_mode():
    dataset = DatasetInput(
        dataframe=pd.DataFrame({"score": [10, 10, 12, 15]}),
        source_type="manual",
        value_column="score",
    )

    result = analyze_dataframe(dataset)

    assert math.isclose(result.mode, 10.0)
