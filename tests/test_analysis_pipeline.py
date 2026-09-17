from api.analysis_pipeline import run_deterministic_analysis_file


def test_deterministic_pipeline_returns_stats_sales_metrics_and_chart():
    result = run_deterministic_analysis_file(
        "tests/fixtures/sample_sales.csv",
        value_column="Revenue",
        date_column="Date",
        category_column="Product",
        units_column="UnitsSold",
        z_score_threshold=2.0,
    )

    assert result["status"] == "ok"
    assert result["llm_enabled"] is False
    assert result["insight"] is None
    assert result["stats"]["total"] == 17360.0
    assert result["sales_metrics"]["total_revenue"] == 17360.0
    assert result["sales_metrics"]["total_units_sold"] == 182.0
    assert result["chart"]["chart_type"] == "line"
