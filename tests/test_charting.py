from core.charting import generate_chart_payload
from core.core_engine import analyze_dataset


def test_generate_chart_payload_returns_plotly_compatible_line_chart():
    result = analyze_dataset(
        "tests/fixtures/sample_sales.csv",
        value_column="Revenue",
        date_column="Date",
        category_column="Product",
        z_score_threshold=2.0,
    )

    payload = generate_chart_payload(result)

    assert payload["chart_type"] == "line"
    assert payload["figure"]["data"][0]["type"] == "scatter"
    assert len(payload["figure"]["data"][0]["x"]) == 10
    assert payload["figure"]["data"][1]["name"] == "Anomalies"
