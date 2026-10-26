import pandas as pd
import pytest
from src.analytics import (
    calculate_line_metrics,
    overall_kpis,
    average_order_value,
    identify_negative_profit_products,
    identify_high_refund_products,
)

@pytest.fixture
def sample_df():
    data = {
        "date": ["2023-01-01", "2023-01-01", "2023-01-02"],
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

def test_revenue_and_profit(sample_df):
    # Gross sales per line
    expected_gross = [200, 200, 300]
    assert list(sample_df["gross_sales"]) == expected_gross
    # Revenue equals gross sales (no refunds)
    assert list(sample_df["revenue"]) == expected_gross
    # Estimated profit calculation
    # line1: 200 - (2*60) -10-5-3 = 200 -120 -18 = 62
    # line2: 200 - (1*150) -5-2-1 = 200 -150 -8 = 42
    # line3: 300 - (3*60) -15-8-4 = 300 -180 -27 = 93
    expected_profit = [62, 42, 93]
    assert list(sample_df["estimated_profit"]) == expected_profit

def test_contribution_margin_zero_revenue():
    df = pd.DataFrame({
        "units": [0],
        "selling_price": [0],
        "unit_cost": [0],
        "platform_fee": [0],
        "shipping_cost": [0],
        "ad_cost": [0],
        "refund_amount": [0],
    })
    df = calculate_line_metrics(df)
    assert df.at[0, "revenue"] == 0
    assert df.at[0, "profit_margin_pct"] is None

def test_overall_kpis(sample_df):
    kpis = overall_kpis(sample_df)
    # Net sales = sum of revenue
    assert kpis["net_sales"] == sum(sample_df["revenue"])
    # Units sold sum
    assert kpis["units_sold"] == sum(sample_df["units"])
    # Unique orders = 2
    assert kpis["unique_orders"] == 2
    # AOV = net_sales / unique_orders
    assert kpis["average_order_value"] == kpis["net_sales"] / 2

def test_negative_profit_alert(sample_df):
    # Manipulate a row to have negative profit
    df = sample_df.copy()
    df.at[0, "estimated_profit"] = -10
    neg = identify_negative_profit_products(df)
    assert not neg.empty
    assert neg.iloc[0]["sku"] == df.iloc[0]["sku"]

def test_high_refund_alert():
    df = pd.DataFrame({
        "sku": ["SKU1", "SKU2"],
        "product_name": ["Prod A", "Prod B"],
        "units": [10, 5],
        "selling_price": [100, 200],
        "unit_cost": [60, 150],
        "platform_fee": [10, 5],
        "shipping_cost": [5, 2],
        "ad_cost": [3, 1],
        "refund_amount": [1500, 0],  # 1500 refund on gross 1000
    })
    df["date"] = pd.to_datetime(["2023-01-01", "2023-01-01"]).date
    df = calculate_line_metrics(df)
    high_refund = identify_high_refund_products(df, threshold_pct=10.0)
    assert not high_refund.empty
    assert high_refund.iloc[0]["sku"] == "SKU1"
    # Refund percent should be > 100%
    assert high_refund.iloc[0]["refund_pct"] > 100
