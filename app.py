"""
Divine Tree Intelligence — E-Commerce Analytics Dashboard
─────────────────────────────────────────────────────────
A Streamlit-based BI dashboard for Divine Tree, an Indian agriculture,
gardening, and plant-care products business.
"""

import os
from html import escape
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.data_loader import load_data, REQUIRED_COLUMNS
from src.exporter import build_excel_report
from src.analytics import (
    calculate_line_metrics,
    overall_kpis,
    daily_summary,
    summarize_by_marketplace,
    summarize_by_sku,
    generate_alerts,
)

# ═══════════════════════════════════════════════════════════
# Page Config & Theme
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Divine Tree Intelligence",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand colours ──
BRAND_GREEN = "#2E7D32"
BRAND_GREEN_LIGHT = "#4CAF50"
BRAND_GREEN_BG = "#E8F5E9"
BRAND_ACCENT = "#1B5E20"
NEUTRAL_BG = "#FAFAFA"
WHITE = "#FFFFFF"
TEXT_DARK = "#212121"
TEXT_SECONDARY = "#616161"
BORDER = "#E0E0E0"
ALERT_RED = "#C62828"
ALERT_AMBER = "#F57F17"

# ── Global CSS ──
st.markdown(
    f"""
    <style>
    /* ── Base ── */
    .stApp {{
        background-color: {NEUTRAL_BG};
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {WHITE} 0%, #F5F5F5 100%);
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 1rem;
    }}

    /* ── KPI Card ── */
    .kpi-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 1.25rem 1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 0.2s ease;
    }}
    .kpi-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}
    .kpi-label {{
        font-size: 0.78rem;
        font-weight: 600;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.35rem;
    }}
    .kpi-value {{
        font-size: 1.55rem;
        font-weight: 700;
        color: {TEXT_DARK};
        line-height: 1.2;
    }}
    .kpi-value.green {{ color: {BRAND_GREEN}; }}
    .kpi-value.red   {{ color: {ALERT_RED}; }}

    /* ── Section Headers ── */
    .section-header {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {TEXT_DARK};
        margin: 2rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid {BRAND_GREEN_LIGHT};
        display: inline-block;
    }}

    /* ── Alert Cards ── */
    .alert-card {{
        background: {WHITE};
        border-left: 4px solid {ALERT_RED};
        border-radius: 8px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .alert-card.warning {{
        border-left-color: {ALERT_AMBER};
    }}
    .alert-title {{
        font-weight: 700;
        font-size: 0.92rem;
        color: {ALERT_RED};
    }}
    .alert-card.warning .alert-title {{
        color: {ALERT_AMBER};
    }}
    .alert-body {{
        font-size: 0.85rem;
        color: {TEXT_SECONDARY};
        margin-top: 0.25rem;
    }}
    .alert-suggestion {{
        font-size: 0.82rem;
        font-style: italic;
        color: {TEXT_SECONDARY};
        margin-top: 0.3rem;
    }}

    /* ── Misc ── */
    .brand-title {{
        font-size: 1.35rem;
        font-weight: 800;
        color: {BRAND_ACCENT};
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    .brand-tagline {{
        font-size: 0.78rem;
        color: {TEXT_SECONDARY};
        margin-top: -0.2rem;
    }}
    .period-badge {{
        display: inline-block;
        background: {BRAND_GREEN_BG};
        color: {BRAND_GREEN};
        font-size: 0.82rem;
        font-weight: 600;
        padding: 0.3rem 0.75rem;
        border-radius: 6px;
    }}
    .empty-state {{
        text-align: center;
        color: {TEXT_SECONDARY};
        padding: 2.5rem 1rem;
        font-size: 0.95rem;
    }}

    /* ── Hide default Streamlit header ── */
    header[data-testid="stHeader"] {{
        background: transparent;
    }}
    /* Tighten top padding */
    .main .block-container {{
        padding-top: 1.5rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
# Helper: Indian number formatting
# ═══════════════════════════════════════════════════════════

def fmt_inr(value: float) -> str:
    """Format a number as ₹ with Indian comma grouping (e.g. ₹1,25,000.00)."""
    if value < 0:
        return f"-₹{fmt_inr_abs(abs(value))}"
    return f"₹{fmt_inr_abs(value)}"


def fmt_inr_abs(v: float) -> str:
    """Return the Indian-grouped string without the ₹ prefix."""
    integer_part, fraction = f"{v:.2f}".split(".")
    s = integer_part
    if len(s) <= 3:
        return s + "." + fraction
    last_three = s[-3:]
    remaining = s[:-3]
    groups = []
    while remaining:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    return ",".join(groups) + "," + last_three + "." + fraction


def fmt_pct(value) -> str:
    if value is None or pd.isna(value):
        return "–"
    return f"{value:.1f}%"


# ═══════════════════════════════════════════════════════════
# Helper: KPI card HTML
# ═══════════════════════════════════════════════════════════

def kpi_card(label: str, value: str, color_class: str = "") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color_class}">{value}</div>
    </div>
    """


# ═══════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<div class="brand-title">🌿 Divine Tree</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-tagline">E-Commerce Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")

    # ── File upload ──
    st.markdown("##### 📂 Data Source")
    uploaded_file = st.file_uploader(
        "Upload Sales Report",
        type=["csv", "xlsx", "xlsm"],
        help="CSV or Excel file with the required schema.",
    )

    # ── Downloadable template ──
    template_csv = ",".join(REQUIRED_COLUMNS) + "\n"
    st.download_button(
        "⬇ Download CSV Template",
        data=template_csv,
        file_name="divine_tree_template.csv",
        mime="text/csv",
    )

    st.markdown("---")


# ═══════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Loading data …")
def load_and_calculate(file_bytes: bytes, filename: str):
    df, msgs = load_data(file_bytes, filename)
    df = calculate_line_metrics(df)
    return df, msgs


data_loaded = False
load_messages = []

try:
    if uploaded_file is not None:
        df_raw, load_messages = load_and_calculate(
            uploaded_file.getvalue(), uploaded_file.name
        )
        data_loaded = True
    else:
        sample_path = os.path.join(
            os.path.dirname(__file__), "sample_data", "sample_sales.csv"
        )
        with open(sample_path, "rb") as f:
            df_raw, load_messages = load_and_calculate(f.read(), "sample_sales.csv")
        data_loaded = True
except Exception as exc:
    st.error(f"**Could not load data:** {exc}")

if not data_loaded:
    st.stop()

# Show validation messages in sidebar
with st.sidebar:
    source_identity = (
        (uploaded_file.name, uploaded_file.size) if uploaded_file is not None else ("sample",)
    )
    if st.session_state.get("_loaded_source_identity") != source_identity:
        st.session_state["_loaded_source_identity"] = source_identity
        st.session_state["_last_loaded_at"] = datetime.now()

    if load_messages:
        st.markdown("##### ⚠️ Data Quality")
        for msg in load_messages:
            st.warning(msg, icon="⚠️")
    else:
        st.success("Data loaded — no quality issues.", icon="✅")

# ═══════════════════════════════════════════════════════════
# Filters
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("---")
    st.markdown("##### 🔍 Filters")

    all_marketplaces = sorted(df_raw["marketplace"].unique().tolist())
    all_skus = sorted(df_raw["sku"].unique().tolist())
    date_min = df_raw["date"].min()
    date_max = df_raw["date"].max()
    file_identity = f"{uploaded_file.name}_{uploaded_file.size}" if uploaded_file else "sample"
    filter_key = f"{file_identity}_{date_min}_{date_max}"
    marketplace_key = f"marketplaces_{filter_key}"
    sku_key = f"skus_{filter_key}"
    start_key = f"start_date_{filter_key}"
    end_key = f"end_date_{filter_key}"
    st.session_state.setdefault(marketplace_key, all_marketplaces)
    st.session_state.setdefault(sku_key, all_skus)
    st.session_state.setdefault(start_key, date_min)
    st.session_state.setdefault(end_key, date_max)
    if st.button("Reset filters", use_container_width=True):
        st.session_state[marketplace_key] = all_marketplaces
        st.session_state[sku_key] = all_skus
        st.session_state[start_key] = date_min
        st.session_state[end_key] = date_max

    # Marketplace
    selected_marketplaces = st.multiselect(
        "Marketplace",
        options=all_marketplaces,
        key=marketplace_key,
    )

    selected_skus = st.multiselect(
        "Product / SKU",
        options=all_skus,
        key=sku_key,
    )

    # Date range
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        selected_start = st.date_input(
            "From", min_value=date_min, max_value=date_max, key=start_key
        )
    with col_d2:
        selected_end = st.date_input(
            "To", min_value=date_min, max_value=date_max, key=end_key
        )

    # Refund alert threshold
    refund_threshold = st.slider(
        "Refund Alert Threshold (%)",
        min_value=1,
        max_value=50,
        value=10,
        help="Flag products whose refund amount exceeds this % of gross sales.",
    )

    st.markdown("---")

    # Data status
    if uploaded_file:
        st.caption(f"📄 **File:** {uploaded_file.name}")
    else:
        st.caption("📄 Using sample data")
    st.caption(
        f"🕓 Last loaded: {st.session_state['_last_loaded_at'].strftime('%d %b %Y, %H:%M')}"
    )

# ── Apply filters ──
mask = (
    df_raw["marketplace"].isin(selected_marketplaces)
    & df_raw["sku"].isin(selected_skus)
    & (df_raw["date"] >= selected_start)
    & (df_raw["date"] <= selected_end)
)
df = df_raw.loc[mask].copy()

# ═══════════════════════════════════════════════════════════
# Page Header
# ═══════════════════════════════════════════════════════════

st.markdown(
    """
    <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
        <span style="font-size:1.85rem; font-weight:800; color:#212121;">
            Divine Tree Intelligence
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f'<span class="period-badge">📅 {selected_start.strftime("%d %b %Y")} — {selected_end.strftime("%d %b %Y")}</span>',
    unsafe_allow_html=True,
)
st.markdown("")

# ═══════════════════════════════════════════════════════════
# KPI Cards
# ═══════════════════════════════════════════════════════════

if df.empty:
    st.markdown(
        '<div class="empty-state">No records match the current filters. '
        "Try adjusting the marketplace or date range.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

kpis = overall_kpis(df)

cols = st.columns(6)
margin_color = "green" if kpis["contribution_margin_pct"] is not None and kpis["contribution_margin_pct"] > 0 else "red"
profit_color = "green" if kpis["estimated_contribution_profit"] >= 0 else "red"

cards = [
    ("Net Sales", fmt_inr(kpis["net_sales"]), ""),
    ("Estimated Contribution Profit", fmt_inr(kpis["estimated_contribution_profit"]), profit_color),
    ("Contribution Margin", fmt_pct(kpis["contribution_margin_pct"]), margin_color),
    ("Units Sold", f'{int(kpis["units_sold"]):,}', ""),
    ("Unique Orders", f'{int(kpis["unique_orders"]):,}', ""),
    ("Avg Order Value", fmt_inr(kpis["average_order_value"]), ""),
]
for col, (label, value, color) in zip(cols, cards):
    col.markdown(kpi_card(label, value, color), unsafe_allow_html=True)

st.markdown("")

# ═══════════════════════════════════════════════════════════
# Charts — Row 1: Daily Trend + Marketplace
# ═══════════════════════════════════════════════════════════

chart_col1, chart_col2 = st.columns([3, 2])

# ── Daily Sales Trend ──
with chart_col1:
    st.markdown('<div class="section-header">📈 Daily Sales Trend</div>', unsafe_allow_html=True)
    daily = daily_summary(df)
    show_profit_overlay = st.checkbox("Show profit overlay", value=False, key="profit_toggle")

    fig_daily = go.Figure()
    fig_daily.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["net_revenue"],
            mode="lines+markers",
            name="Net Revenue",
            line=dict(color=BRAND_GREEN, width=2.5),
            marker=dict(size=5),
            hovertemplate="₹%{y:,.0f}<extra>Revenue</extra>",
        )
    )
    if show_profit_overlay:
        fig_daily.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["estimated_profit"],
                mode="lines+markers",
                name="Estimated Contribution Profit",
                line=dict(color="#FF9800", width=2, dash="dot"),
                marker=dict(size=4),
                hovertemplate="₹%{y:,.0f}<extra>Profit</extra>",
            )
        )

    fig_daily.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="top", y=1.12, xanchor="left", x=0),
        xaxis_title=None,
        yaxis_title=None,
        yaxis_tickprefix="₹",
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# ── Marketplace Performance ──
with chart_col2:
    st.markdown('<div class="section-header">🏪 Marketplace Performance</div>', unsafe_allow_html=True)
    market = summarize_by_marketplace(df)
    mp_metric = st.radio(
        "View", ["Net Revenue", "Estimated Contribution Profit"], horizontal=True, key="mp_metric"
    )
    y_col = "net_revenue" if mp_metric == "Net Revenue" else "estimated_profit"
    bar_color = BRAND_GREEN if mp_metric == "Net Revenue" else "#FF9800"

    fig_mp = px.bar(
        market.sort_values(y_col, ascending=True),
        y="marketplace",
        x=y_col,
        orientation="h",
        text_auto=",.0f",
        color_discrete_sequence=[bar_color],
    )
    fig_mp.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=None,
        yaxis_title=None,
        xaxis_tickprefix="₹",
        showlegend=False,
    )
    fig_mp.update_traces(textposition="auto", textfont_size=11)
    st.plotly_chart(fig_mp, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# Top Products — Revenue vs Profit (side-by-side)
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-header">🏆 Top Products</div>', unsafe_allow_html=True)

sku_all = summarize_by_sku(df)

top_col1, top_col2 = st.columns(2)

with top_col1:
    st.markdown("**Top 5 by Net Revenue**")
    top_rev = sku_all.nlargest(5, "net_revenue")[["sku", "product_name", "net_revenue"]].copy()
    top_rev["net_revenue"] = top_rev["net_revenue"].apply(fmt_inr)
    top_rev = top_rev.rename(columns={"sku": "SKU", "product_name": "Product", "net_revenue": "Net Revenue"})
    st.dataframe(top_rev, use_container_width=True, hide_index=True)

with top_col2:
    st.markdown("**Top 5 by Estimated Contribution Profit**")
    top_profit = sku_all.nlargest(5, "estimated_profit")[["sku", "product_name", "estimated_profit"]].copy()
    top_profit = top_profit.rename(columns={"sku": "SKU", "product_name": "Product", "estimated_profit": "Estimated Contribution Profit"})
    st.dataframe(
        top_profit,
        use_container_width=True,
        hide_index=True,
        column_config={"Estimated Contribution Profit": st.column_config.NumberColumn(format="₹%.2f")},
    )

# ═══════════════════════════════════════════════════════════
# Product Performance Table
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📦 Product Performance</div>', unsafe_allow_html=True)

display_sku = sku_all.copy()
display_sku = display_sku.rename(
    columns={
        "sku": "SKU",
        "product_name": "Product Name",
        "units_sold": "Units Sold",
        "net_revenue": "Net Revenue",
        "estimated_profit": "Estimated Contribution Profit",
        "contribution_margin_pct": "Margin %",
        "total_refund": "Refund Amt",
    }
)
st.dataframe(
    display_sku,
    use_container_width=True,
    hide_index=True,
    height=min(400, 56 + len(display_sku) * 35),
    column_config={
        "Net Revenue": st.column_config.NumberColumn(format="₹%.2f"),
        "Estimated Contribution Profit": st.column_config.NumberColumn(format="₹%.2f"),
        "Refund Amt": st.column_config.NumberColumn(format="₹%.2f"),
        "Margin %": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

# ═══════════════════════════════════════════════════════════
# Business Alerts
# ═══════════════════════════════════════════════════════════

st.markdown(
    f'<div class="section-header">🚨 Business Alerts</div>'
    f'<span style="font-size:0.8rem;color:{TEXT_SECONDARY};">'
    f"Refund threshold: {refund_threshold}% of gross sales</span>",
    unsafe_allow_html=True,
)

alerts = generate_alerts(df, refund_threshold=float(refund_threshold))

if not alerts:
    st.success("✅ No alerts for the selected period. All products appear healthy.")
else:
    for alert in alerts:
        card_class = "warning" if alert["title"] == "High Refund Ratio" else ""
        st.markdown(
            f"""
            <div class="alert-card {card_class}">
                <div class="alert-title">{escape(str(alert['title']))}</div>
                <div class="alert-body">
                    <strong>{escape(str(alert['product_name']))}</strong> (SKU: {escape(str(alert['sku']))})
                    — {escape(str(alert['reason']))} &nbsp;•&nbsp; <strong>{escape(str(alert['value']))}</strong>
                </div>
                <div class="alert-suggestion">💡 {escape(str(alert['suggestion']))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════
# Excel Export
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📥 Export Report</div>', unsafe_allow_html=True)

export_col1, export_col2 = st.columns([1, 4])
with export_col1:
    if st.button("Generate Excel Report", type="primary"):
        report = build_excel_report(df, sku_all, market, daily, alerts)
        st.download_button(
            "⬇ Download Excel",
            data=report,
            file_name=f"DivineTree_Report_{selected_start}_to_{selected_end}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ═══════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align:center; font-size:0.78rem; color:{TEXT_SECONDARY}; padding: 0.5rem;">
        <strong>Divine Tree Intelligence</strong> — Internal prototype.
        Data is processed locally; nothing is sent to external services.<br>
        For production deployment, implement access control and secure hosting.
    </div>
    """,
    unsafe_allow_html=True,
)
