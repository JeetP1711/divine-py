import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime
from src.data_loader import load_data
from src.analytics import (
    calculate_line_metrics,
    overall_kpis,
    daily_summary,
    summarize_by_marketplace,
    summarize_by_sku,
    generate_alerts,
    average_order_value,
)

st.set_page_config(page_title="Divine Tree Intelligence", layout="wide")

# ----- Sidebar -----
st.sidebar.title("Divine Tree")
st.sidebar.markdown("---")

# File upload
uploaded_file = st.sidebar.file_uploader(
    "Upload sales data (CSV or Excel)", type=["csv", "xlsx", "xls"], help="The file must contain the required columns."
)

# Marketplace filter placeholder (populated after data load)
marketplace_options = []
selected_marketplaces = []

# Date range filter placeholder
date_min = None
date_max = None
selected_start = None
selected_end = None

# Reset filters button
reset = st.sidebar.button("Reset filters")

# Data status
if uploaded_file is not None:
    st.sidebar.info(f"File: {uploaded_file.name}")
else:
    st.sidebar.info("No file uploaded – using sample data.")

# ----- Load Data -----
@st.cache_data(show_spinner=False)
def get_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    df, messages = load_data(file_bytes, filename)
    # Add calculated columns
    df = calculate_line_metrics(df)
    # Show validation messages if any
    for msg in messages:
        st.sidebar.warning(msg)
    return df

if uploaded_file is not None:
    df = get_dataframe(uploaded_file.getvalue(), uploaded_file.name)
else:
    # Load sample data from assets
    sample_path = "sample_data/sample_sales.csv"
    with open(sample_path, "rb") as f:
        df = get_dataframe(f.read(), "sample_sales.csv")

# ----- Filters -----
if reset:
    st.experimental_rerun()

# Marketplace multi‑select
marketplace_options = sorted(df["marketplace"].unique().tolist())
selected_marketplaces = st.sidebar.multiselect(
    "Marketplace", options=marketplace_options, default=marketplace_options
)

# Date range
date_min = df["date"].min()
date_max = df["date"].max()
selected_start = st.sidebar.date_input("Start date", value=date_min, min_value=date_min, max_value=date_max)
selected_end = st.sidebar.date_input("End date", value=date_max, min_value=date_min, max_value=date_max)

# Apply filters
mask = (
    df["marketplace"].isin(selected_marketplaces)
    & (df["date"] >= pd.to_datetime(selected_start))
    & (df["date"] <= pd.to_datetime(selected_end))
)
filtered_df = df[mask]

# ----- KPI Cards -----
st.title("Divine Tree Intelligence Dashboard")
st.subheader(f"Reporting period: {selected_start} to {selected_end}")

kpis = overall_kpis(filtered_df)
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Net Sales", f"₹{kpis['net_sales']:, .2f}")
col2.metric("Estimated Contribution Profit", f"₹{kpis['estimated_contribution_profit']:, .2f}")
margin_display = f"{kpis['contribution_margin_pct']:.2f}%" if kpis['contribution_margin_pct'] is not None else "‑"
col3.metric("Contribution Margin", margin_display)
col4.metric("Units Sold", f"{int(kpis['units_sold']):,}")
col5.metric("Unique Orders", f"{int(kpis['unique_orders']):,}")
col6.metric("Average Order Value", f"₹{kpis['average_order_value']:, .2f}")

# ----- Charts -----
# Daily sales trend
st.markdown("---")
st.header("Daily Sales Trend")
if not filtered_df.empty:
    daily = daily_summary(filtered_df)
    fig = px.line(daily, x="date", y="net_revenue", title="Net Revenue Over Time", markers=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected filters.")

# Marketplace performance
st.header("Marketplace Performance")
if not filtered_df.empty:
    market = summarize_by_marketplace(filtered_df)
    metric = st.radio("Metric", ["Net Revenue", "Estimated Profit"], index=0, horizontal=True)
    y_col = "net_revenue" if metric == "Net Revenue" else "estimated_profit"
    fig2 = px.bar(market, x="marketplace", y=y_col, title=f"{metric} by Marketplace", text_auto=True)
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No data for selected filters.")

# Product performance table
st.header("Product Performance")
if not filtered_df.empty:
    sku_summary = summarize_by_sku(filtered_df)
    sku_summary = sku_summary.rename(columns={
        "sku": "SKU",
        "product_name": "Product Name",
        "units_sold": "Units Sold",
        "net_revenue": "Net Revenue",
        "estimated_profit": "Estimated Profit",
        "contribution_margin_pct": "Contribution Margin %",
        "total_refund": "Refund Amount",
    })
    sku_summary["Net Revenue"] = sku_summary["Net Revenue"].apply(lambda x: f"₹{x:,.2f}")
    sku_summary["Estimated Profit"] = sku_summary["Estimated Profit"].apply(lambda x: f"₹{x:,.2f}")
    sku_summary["Refund Amount"] = sku_summary["Refund Amount"].apply(lambda x: f"₹{x:,.2f}")
    sku_summary["Contribution Margin %"] = sku_summary["Contribution Margin %"].apply(
        lambda x: f"{x:.2f}%" if pd.notnull(x) else "‑"
    )
    st.dataframe(sku_summary, use_container_width=True)
else:
    st.info("No data for selected filters.")

# Alerts
st.header("Business Alerts")
if not filtered_df.empty:
    alerts = generate_alerts(filtered_df)
    if alerts:
        for alert in alerts:
            st.warning(f"**{alert['title']}** – {alert['product_name']} (SKU: {alert['sku']}): {alert['reason']} – {alert['value']}. *{alert['suggestion']}*")
    else:
        st.success("No alerts for the selected period.")
else:
    st.info("No data for selected filters.")

# Excel export
st.header("Export Report")
if st.button("Export to Excel"):
    import pandas as pd
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sales Details
        filtered_df.to_excel(writer, sheet_name="Sales Details", index=False)
        # Product Summary
        sku_summary.to_excel(writer, sheet_name="Product Summary", index=False)
        # Marketplace Summary
        market.to_excel(writer, sheet_name="Marketplace Summary", index=False)
        # Daily Summary
        daily.to_excel(writer, sheet_name="Daily Summary", index=False)
        # Alerts
        alerts_df = pd.DataFrame(alerts)
        if not alerts_df.empty:
            alerts_df.to_excel(writer, sheet_name="Business Alerts", index=False)
    output.seek(0)
    today = datetime.now().strftime("%Y%m%d")
    st.download_button(
        label="Download Excel",
        data=output,
        file_name=f"Divine_Tree_Report_{selected_start}_to_{selected_end}_{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
