"""Tests for src/analytics.py — core business calculations."""

import pandas as pd
import pytest

from src.analytics import (
    calculate_line_metrics,
    overall_kpis,
    average_order_value,
    summarize_by_sku,
    summarize_by_marketplace,
    daily_summary,
    identify_negative_profit_products,
    identify_high_refund_products,
    generate_alerts,
)


# ────────────────────────── Fixtures ──────────────────────────


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Three order‑lines spanning two orders and two marketplaces."""
    data = {
        "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "order_id": ["ORD1", "ORD1", "ORD2"],
        "marketplace": ["Amazon", "Amazon", "Flipkart"],
        "sku": ["SKU1", "SKU2", "SKU1"],
        "product_name": ["Prod A", "Prod B", "Prod A"],
        "units": [2, 1, 3],
        "selling_price": [100, 200, 100],
        "unit_cost": [60, 150, 60],
        "platform_fee": [10, 5, 15],
        "shipping_cost": [5, 2, 8],
        "ad_cost": [3, 1, 4],
        "refund_amount": [0, 0, 0],
    }
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return calculate_line_metrics(df)


# ──────────────────── Revenue & Profit Tests ────────────────────


def test_gross_sales(sample_df: pd.DataFrame):
    assert list(sample_df["gross_sales"]) == [200, 200, 300]


def test_revenue_equals_gross_when_no_refund(sample_df: pd.DataFrame):
    assert list(sample_df["revenue"]) == [200, 200, 300]


def test_estimated_profit(sample_df: pd.DataFrame):
    # line1: 200 - 120 - 10 - 5 - 3  = 62
    # line2: 200 - 150 -  5 - 2 - 1  = 42
    # line3: 300 - 180 - 15 - 8 - 4  = 93
    assert list(sample_df["estimated_profit"]) == [62, 42, 93]


def test_profit_margin_pct(sample_df: pd.DataFrame):
    expected = [62 / 200 * 100, 42 / 200 * 100, 93 / 300 * 100]
    for actual, exp in zip(sample_df["profit_margin_pct"], expected):
        assert abs(actual - exp) < 0.01


def test_revenue_with_refund():
    df = pd.DataFrame(
        {
            "units": [5],
            "selling_price": [200],
            "unit_cost": [80],
            "platform_fee": [50],
            "shipping_cost": [30],
            "ad_cost": [10],
            "refund_amount": [200],
        }
    )
    df = calculate_line_metrics(df)
    assert df.at[0, "gross_sales"] == 1000
    assert df.at[0, "revenue"] == 800  # 1000 - 200
    assert df.at[0, "estimated_profit"] == 800 - 400 - 50 - 30 - 10  # = 310


# ──────────────────── Zero / Edge‑case Tests ────────────────────


def test_zero_revenue_gives_none_margin():
    df = pd.DataFrame(
        {
            "units": [0],
            "selling_price": [0],
            "unit_cost": [0],
            "platform_fee": [0],
            "shipping_cost": [0],
            "ad_cost": [0],
            "refund_amount": [0],
        }
    )
    df = calculate_line_metrics(df)
    assert df.at[0, "revenue"] == 0
    assert df.at[0, "profit_margin_pct"] is None


def test_empty_dataframe():
    df = pd.DataFrame(
        columns=[
            "date",
            "order_id",
            "marketplace",
            "sku",
            "product_name",
            "units",
            "selling_price",
            "unit_cost",
            "platform_fee",
            "shipping_cost",
            "ad_cost",
            "refund_amount",
        ]
    )
    df = calculate_line_metrics(df)
    kpis = overall_kpis(df)
    assert kpis["net_sales"] == 0
    assert kpis["units_sold"] == 0
    assert kpis["unique_orders"] == 0
    assert kpis["average_order_value"] == 0.0
    assert kpis["contribution_margin_pct"] is None


# ──────────────────── KPI Tests ────────────────────


def test_overall_kpis(sample_df: pd.DataFrame):
    kpis = overall_kpis(sample_df)
    assert kpis["net_sales"] == 700  # 200+200+300
    assert kpis["estimated_contribution_profit"] == 197  # 62+42+93
    assert kpis["units_sold"] == 6
    assert kpis["unique_orders"] == 2
    assert kpis["average_order_value"] == 350.0  # 700/2
    expected_margin = 197 / 700 * 100
    assert abs(kpis["contribution_margin_pct"] - expected_margin) < 0.01


def test_multi_sku_order_counts_once(sample_df: pd.DataFrame):
    """ORD1 has 2 SKUs — it must still count as 1 unique order."""
    kpis = overall_kpis(sample_df)
    assert kpis["unique_orders"] == 2


def test_aov_uses_unique_orders(sample_df: pd.DataFrame):
    kpis = overall_kpis(sample_df)
    # AOV = total_revenue / unique_orders, NOT / number_of_lines
    assert kpis["average_order_value"] == kpis["net_sales"] / 2


# ──────────────────── Aggregation Tests ────────────────────


def test_summarize_by_sku(sample_df: pd.DataFrame):
    sku = summarize_by_sku(sample_df)
    # SKU1 appears in two lines: 2 + 3 = 5 units, revenue = 200 + 300 = 500
    sku1 = sku[sku["sku"] == "SKU1"].iloc[0]
    assert sku1["units_sold"] == 5
    assert sku1["net_revenue"] == 500
    assert sku1["estimated_profit"] == 62 + 93  # = 155

    sku2 = sku[sku["sku"] == "SKU2"].iloc[0]
    assert sku2["units_sold"] == 1
    assert sku2["net_revenue"] == 200


def test_summarize_by_marketplace(sample_df: pd.DataFrame):
    market = summarize_by_marketplace(sample_df)
    amazon = market[market["marketplace"] == "Amazon"].iloc[0]
    assert amazon["net_revenue"] == 400  # 200 + 200
    flipkart = market[market["marketplace"] == "Flipkart"].iloc[0]
    assert flipkart["net_revenue"] == 300


def test_daily_summary(sample_df: pd.DataFrame):
    daily = daily_summary(sample_df)
    assert len(daily) == 2
    day1 = daily[daily["date"] == pd.Timestamp("2024-01-01").date()].iloc[0]
    assert day1["net_revenue"] == 400


# ──────────────────── Alert Tests ────────────────────


def test_negative_profit_detection():
    """Create a product that is definitely loss‑making."""
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01"]).date,
            "order_id": ["O1"],
            "marketplace": ["Amazon"],
            "sku": ["LOSS"],
            "product_name": ["Bad Product"],
            "units": [1],
            "selling_price": [100],
            "unit_cost": [90],
            "platform_fee": [15],
            "shipping_cost": [10],
            "ad_cost": [5],
            "refund_amount": [0],
        }
    )
    df = calculate_line_metrics(df)
    # profit = 100 - 90 - 15 - 10 - 5 = -20
    assert df.at[0, "estimated_profit"] == -20
    neg = identify_negative_profit_products(df)
    assert len(neg) == 1
    assert neg.iloc[0]["sku"] == "LOSS"


def test_high_refund_detection():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01"]).date,
            "order_id": ["O1", "O2"],
            "marketplace": ["Amazon", "Amazon"],
            "sku": ["SKU-HR", "SKU-OK"],
            "product_name": ["High Refund", "Low Refund"],
            "units": [10, 5],
            "selling_price": [100, 200],
            "unit_cost": [60, 150],
            "platform_fee": [10, 5],
            "shipping_cost": [5, 2],
            "ad_cost": [3, 1],
            "refund_amount": [150, 0],
        }
    )
    df = calculate_line_metrics(df)
    # SKU-HR gross = 1000, refund = 150 => 15% => above 10% threshold
    high = identify_high_refund_products(df, threshold_pct=10.0)
    assert len(high) == 1
    assert high.iloc[0]["sku"] == "SKU-HR"
    assert high.iloc[0]["refund_pct"] == pytest.approx(15.0)


def test_generate_alerts_includes_both_types():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01"]).date,
            "order_id": ["O1", "O2"],
            "marketplace": ["Amazon", "Amazon"],
            "sku": ["LOSS", "REFUND"],
            "product_name": ["Loss Maker", "Refund Heavy"],
            "units": [1, 10],
            "selling_price": [100, 100],
            "unit_cost": [90, 50],
            "platform_fee": [15, 10],
            "shipping_cost": [10, 5],
            "ad_cost": [5, 3],
            "refund_amount": [0, 150],
        }
    )
    df = calculate_line_metrics(df)
    alerts = generate_alerts(df, refund_threshold=10.0)
    titles = [a["title"] for a in alerts]
    assert "Negative Profit" in titles
    assert "High Refund Ratio" in titles


# ──────────────────── Filtering Consistency ────────────────────


def test_filtered_kpis_match_subset(sample_df: pd.DataFrame):
    """KPIs on a filtered subset must equal hand‑calculations on that subset."""
    amazon_only = sample_df[sample_df["marketplace"] == "Amazon"]
    kpis = overall_kpis(amazon_only)
    assert kpis["net_sales"] == 400
    assert kpis["unique_orders"] == 1  # only ORD1 on Amazon
    assert kpis["average_order_value"] == 400.0
