from typing import Dict, List

import pandas as pd


def _margin_pct(profit: pd.Series, revenue: pd.Series) -> pd.Series:
    margin = profit.div(revenue).mul(100)
    return margin.astype(object).where(revenue.ne(0), None)


# --- Calculation Functions ---

def calculate_line_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add calculated columns to each order line.
    Returns a DataFrame with additional columns:
    - gross_sales
    - revenue
    - cost_of_goods
    - estimated_profit
    - profit_margin_pct
    """
    df = df.copy()
    df["gross_sales"] = df["units"] * df["selling_price"]
    df["revenue"] = df["gross_sales"] - df["refund_amount"]
    df["cost_of_goods"] = df["units"] * df["unit_cost"]
    df["estimated_profit"] = (
        df["revenue"]
        - df["cost_of_goods"]
        - df["platform_fee"]
        - df["shipping_cost"]
        - df["ad_cost"]
    )
    df["profit_margin_pct"] = _margin_pct(df["estimated_profit"], df["revenue"])
    return df


def summarize_by_sku(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics per SKU/product.
    Returns DataFrame indexed by SKU with aggregated columns.
    """
    agg = (
        df.groupby(["sku", "product_name"], as_index=False)
        .agg(
            units_sold=pd.NamedAgg(column="units", aggfunc="sum"),
            net_revenue=pd.NamedAgg(column="revenue", aggfunc="sum"),
            estimated_profit=pd.NamedAgg(column="estimated_profit", aggfunc="sum"),
            total_refund=pd.NamedAgg(column="refund_amount", aggfunc="sum"),
        )
    )
    # Contribution margin per SKU
    agg["contribution_margin_pct"] = _margin_pct(agg["estimated_profit"], agg["net_revenue"])
    return agg


def summarize_by_marketplace(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate revenue and profit per marketplace."""
    agg = (
        df.groupby("marketplace", as_index=False)
        .agg(
            net_revenue=pd.NamedAgg(column="revenue", aggfunc="sum"),
            estimated_profit=pd.NamedAgg(column="estimated_profit", aggfunc="sum"),
        )
    )
    agg["contribution_margin_pct"] = _margin_pct(agg["estimated_profit"], agg["net_revenue"])
    return agg


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate net revenue and profit per date."""
    agg = (
        df.groupby("date", as_index=False)
        .agg(
            net_revenue=pd.NamedAgg(column="revenue", aggfunc="sum"),
            estimated_profit=pd.NamedAgg(column="estimated_profit", aggfunc="sum"),
        )
    )
    agg["contribution_margin_pct"] = _margin_pct(agg["estimated_profit"], agg["net_revenue"])
    return agg


def identify_negative_profit_products(df: pd.DataFrame) -> pd.DataFrame:
    """Return SKU rows where estimated profit is negative.
    Uses the aggregated SKU summary.
    """
    sku_summary = summarize_by_sku(df)
    return sku_summary[sku_summary["estimated_profit"] < 0]


def identify_high_refund_products(df: pd.DataFrame, threshold_pct: float = 10.0) -> pd.DataFrame:
    """Products where refund amount exceeds threshold_pct of gross sales.
    Returns aggregated SKU rows.
    """
    sku = (
        df.groupby(["sku", "product_name"], as_index=False)
        .agg(
            gross_sales=pd.NamedAgg(column="gross_sales", aggfunc="sum"),
            total_refund=pd.NamedAgg(column="refund_amount", aggfunc="sum"),
        )
    )
    sku["refund_pct"] = (
        sku["total_refund"].div(sku["gross_sales"]).mul(100).where(sku["gross_sales"].ne(0))
    )
    return sku[sku["refund_pct"].ge(threshold_pct)]


def average_order_value(df: pd.DataFrame) -> float:
    """Calculate AOV: total net revenue / number of unique orders."""
    total_revenue = df["revenue"].sum()
    unique_orders = df["order_id"].nunique()
    return total_revenue / unique_orders if unique_orders != 0 else 0.0


def overall_kpis(df: pd.DataFrame) -> Dict[str, float]:
    """Compute top‑level KPI values for the current filtered DataFrame.
    Returns a dict with keys:
    - net_sales
    - estimated_contribution_profit
    - contribution_margin_pct
    - units_sold
    - unique_orders
    - average_order_value
    """
    net_sales = df["revenue"].sum()
    profit = df["estimated_profit"].sum()
    margin = (profit / net_sales * 100) if net_sales != 0 else None
    units = df["units"].sum()
    orders = df["order_id"].nunique()
    aov = net_sales / orders if orders != 0 else 0.0
    return {
        "net_sales": net_sales,
        "estimated_contribution_profit": profit,
        "contribution_margin_pct": margin,
        "units_sold": units,
        "unique_orders": orders,
        "average_order_value": aov,
    }

# --- Helper Functions for Alerts ---

def generate_alerts(df: pd.DataFrame, refund_threshold: float = 10.0) -> List[Dict[str, str]]:
    """Create alert dictionaries for UI display.
    Each alert contains: title, sku, product_name, reason, value, suggestion.
    """
    alerts: List[Dict[str, str]] = []
    # Negative profit
    neg = identify_negative_profit_products(df)
    for _, row in neg.iterrows():
        margin = row["contribution_margin_pct"]
        reason = "Estimated contribution profit is negative"
        if margin is not None and not pd.isna(margin) and margin < 0:
            reason += f" and contribution margin is {margin:.1f}%"
        alerts.append({
            "title": "Negative Profit",
            "sku": row["sku"],
            "product_name": row["product_name"],
            "reason": reason,
            "value": f"₹{row['estimated_profit']:.2f}",
            "suggestion": "Review cost structure and pricing for this product.",
        })
    # Surface break-even products separately without duplicating loss-making alerts.
    sku_summary = summarize_by_sku(df)
    zero_margin = sku_summary[
        (sku_summary["estimated_profit"] >= 0)
        & sku_summary["contribution_margin_pct"].le(0)
    ]
    for _, row in zero_margin.iterrows():
        alerts.append({
            "title": "Zero or Negative Margin",
            "sku": row["sku"],
            "product_name": row["product_name"],
            "reason": "Estimated contribution margin is zero or negative",
            "value": f"{row['contribution_margin_pct']:.1f}%",
            "suggestion": "Investigate whether all line-level costs and discounts are represented.",
        })

    zero_cost_products = df.loc[df["unit_cost"].eq(0), ["sku", "product_name"]].drop_duplicates()
    for _, row in zero_cost_products.iterrows():
        alerts.append({
            "title": "Suspicious Cost Information",
            "sku": row["sku"],
            "product_name": row["product_name"],
            "reason": "One or more sales lines have a unit cost of ₹0",
            "value": "₹0 unit cost",
            "suggestion": "Confirm the product cost before using its profitability estimate.",
        })
    # High refund
    high_refund = identify_high_refund_products(df, threshold_pct=refund_threshold)
    for _, row in high_refund.iterrows():
        alerts.append({
            "title": "High Refund Ratio",
            "sku": row["sku"],
            "product_name": row["product_name"],
            "reason": f"Refunds are {row['refund_pct']:.1f}% of gross sales",
            "value": f"₹{row['total_refund']:.2f}",
            "suggestion": "Investigate the refund reasons and product or fulfillment issues.",
        })
    return alerts
