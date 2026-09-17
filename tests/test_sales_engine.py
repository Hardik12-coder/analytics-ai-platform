import pandas as pd

from core.sales_engine import analyze_sales_dataframe


def test_sales_engine_computes_revenue_profit_units_and_monthly_metrics():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-05", "2026-01-20", "2026-02-01", "2026-02-15"],
            "Product": ["A", "B", "A", "B"],
            "Revenue": [1000, 2000, 1500, 2500],
            "Profit": [200, 500, 300, 700],
            "UnitsSold": [10, 20, 15, 25],
        }
    )

    result = analyze_sales_dataframe(
        df,
        revenue_column="Revenue",
        date_column="Date",
        profit_column="Profit",
        units_column="UnitsSold",
        category_column="Product",
    )

    assert result["total_revenue"] == 7000.0
    assert result["total_profit"] == 1700.0
    assert result["profit_margin_pct"] == 24.29
    assert result["total_units_sold"] == 70.0
    assert result["monthly_summary"]["average_monthly_revenue"] == 3500.0
    assert result["monthly_summary"]["median_monthly_revenue"] == 3500.0
    assert result["monthly_summary"]["first_to_last_month_growth_pct"] == 33.33
    assert result["monthly_metrics"][1]["revenue_mom_growth_pct"] == 33.33
    assert result["category_metrics"][0]["category"] == "B"


def test_sales_engine_works_without_optional_columns():
    df = pd.DataFrame({"Revenue": ["$1,000", "$2,500"]})

    result = analyze_sales_dataframe(df, revenue_column="Revenue")

    assert result["transaction_count"] == 2
    assert result["total_revenue"] == 3500.0
    assert result["total_profit"] is None
    assert result["profit_margin_pct"] is None
    assert result["monthly_metrics"] == []
    assert result["category_metrics"] == []
