# 🌿 Divine Tree Intelligence

**E-Commerce Analytics Dashboard** for Divine Tree — an Indian agriculture, gardening, and plant-care products business.

Built with Python, Streamlit, Pandas, Plotly, and OpenPyXL.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **KPI Dashboard** | Net Sales, Est. Contribution Profit, Margin %, Units, Orders, AOV |
| **Daily Sales Trend** | Interactive line chart with optional profit overlay |
| **Marketplace Performance** | Horizontal bar chart comparing revenue or profit across marketplaces |
| **Top Products** | Separate Top-5 lists by revenue and by profit |
| **Product Performance Table** | Full SKU-level table with sortable columns |
| **Business Alerts** | Negative-profit and high-refund alerts with configurable thresholds |
| **Excel Export** | Multi-sheet .xlsx report generated in-memory |
| **CSV Template** | Downloadable template for data preparation |
| **Sample Data** | Built-in dataset so users can explore immediately |
| **Indian Formatting** | ₹ currency with Indian comma grouping (e.g. ₹1,25,000.00) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or later
- pip

### Installation

```bash
# Clone the repository (or copy the folder to your machine)
cd divine-tree

# (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Run the Dashboard

```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501**.

The app loads with sample data automatically — no upload required.

---

## 📁 Project Structure

```
divine-tree/
├── app.py                     # Streamlit dashboard (UI)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── data_loader.py         # File upload, validation, normalisation
│   └── analytics.py           # Business calculations, aggregations, alerts
├── tests/
│   └── test_analytics.py      # 17 Pytest tests for core logic
├── sample_data/
│   └── sample_sales.csv       # 31-row sample dataset (fictional data)
└── assets/
    └── .gitkeep
```

---

## 📊 Required Data Schema

Your uploaded CSV or Excel file **must** contain exactly these columns (case-insensitive):

| Column | Type | Description |
|--------|------|-------------|
| `date` | Date | Order date (YYYY-MM-DD or any parsable format) |
| `order_id` | Text | Unique order identifier |
| `marketplace` | Text | Source marketplace (e.g., Amazon, Flipkart, Meesho) |
| `sku` | Text | Stock-keeping unit code |
| `product_name` | Text | Human-readable product name |
| `units` | Number | Net fulfilled units |
| `selling_price` | Number | Per-unit selling price (₹) |
| `unit_cost` | Number | Per-unit cost of goods (₹) |
| `platform_fee` | Number | Total platform fee for the line (₹) |
| `shipping_cost` | Number | Total shipping cost for the line (₹) |
| `ad_cost` | Number | Total advertising cost for the line (₹) |
| `refund_amount` | Number | Total refund amount for the line (₹) |

**Notes:**
- Each row = one order line. An order can have multiple lines (multiple SKUs).
- `selling_price` and `unit_cost` are **per-unit**; other cost columns are **totals** for the line.
- Missing values are reported — they are **never** silently set to zero.
- A downloadable CSV template is available in the sidebar.

---

## 🧮 Core Formulas

```
Gross Sales           = units × selling_price
Net Revenue           = gross_sales − refund_amount
Cost of Goods         = units × unit_cost
Est. Contribution Profit = revenue − cost_of_goods − platform_fee − shipping_cost − ad_cost
Profit Margin %       = est. profit / revenue × 100   (undefined when revenue = 0)
Average Order Value   = total net revenue / count of unique order_ids
```

**Important:** These are *estimated contribution profits*, not formal accounting profits. GST, packaging, warehousing, overhead, and marketplace settlement adjustments are **not** included unless supplied in the data.

Aggregated margins use `total_profit / total_revenue`, not the average of individual row margins.

---

## 🧪 Running Tests

```bash
python -m pytest tests/test_analytics.py -v
```

**17 tests** covering:
- Gross sales, revenue, profit, and margin calculations
- Zero-revenue edge case
- Empty dataset handling
- Overall KPIs and AOV
- Multi-SKU order counting
- SKU, marketplace, and daily aggregations
- Negative-profit and high-refund alert detection
- Combined alert generation
- Filtered subset consistency

---

## 🔒 Privacy & Security

- **No external data transmission** — all processing happens locally.
- **In-memory processing** — uploaded files are not written to disk.
- **File validation** — type and schema checks before processing.
- **No credentials stored** — nothing sensitive in the codebase.

> ⚠️ This is an internal prototype. For production deployment, add authentication, HTTPS, access control, and proper data protection.

---

## ⚠️ Known Limitations

1. **Large files** may impact performance (everything is in-memory pandas).
2. **No marketplace-specific adapters** — the MVP requires the normalised schema.
3. **No persistent storage** — data resets on page refresh.
4. **No multi-user access** — single local Streamlit instance.
5. **Indian number formatting** is custom (not locale-based).

---

## 🗺️ Future Roadmap (Not Yet Implemented)

- Amazon SP-API / Flipkart / Meesho report adapters
- Website analytics integration
- SKU master & cost catalog
- Inventory forecasting & reorder recommendations
- Scheduled email reports
- AI-generated management summaries
- Multi-user access & cloud deployment

---

## 📜 License

Internal prototype — adapt and extend as needed for your business.
