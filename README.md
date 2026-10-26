# Divine Tree Intelligence Dashboard

## Overview

**Divine Tree Intelligence** is a lightweight, business‑ready analytics dashboard built with **Python**, **Streamlit**, **Pandas**, and **Plotly**. It helps the management of Divine Tree (an Indian agriculture & gardening products business) to explore sales performance, profitability, marketplace comparison, and product‑level insights.

The application:
- Loads CSV or Excel sales reports (with a defined schema).
- Validates and normalises the data.
- Calculates key metrics such as net sales, estimated contribution profit, contribution margin, units sold, unique orders, and average order value.
- Provides interactive KPI cards, trend charts, marketplace comparison, product performance tables, and rule‑based alerts.
- Allows exporting the analysed data to a downloadable Excel workbook.

## Project Structure

```
Divine Tree Intelligence/
├─ app.py                     # Streamlit UI entry point
├─ requirements.txt           # Python dependencies
├─ README.md                  # This file
├─ .gitignore                 # Ignored files
├─ src/
│   ├─ __init__.py
│   ├─ data_loader.py         # File upload & validation
│   └─ analytics.py           # Business calculations & alerts
├─ tests/
│   └─ test_analytics.py     # Pytest suite for core logic
├─ sample_data/
│   └─ sample_sales.csv       # Sample dataset for demo
└─ assets/
    └─ .gitkeep              # Placeholder for future assets
```

## Installation

1. **Clone the repository** (or copy the folder to your machine).
2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   # source venv/bin/activate   # macOS/Linux
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the dashboard**:
   ```bash
   streamlit run app.py
   ```
   The app will open in your default browser at `http://localhost:8501`.

## Data Schema

The uploaded file must contain **exactly** the following columns (case‑insensitive, spaces will be trimmed):

| Column | Description |
|--------|-------------|
| `date` | Order date (YYYY‑MM‑DD or any parseable format) |
| `order_id` | Unique order identifier |
| `marketplace` | Marketplace name (e.g., Amazon, Flipkart) |
| `sku` | Stock‑keeping unit identifier |
| `product_name` | Human‑readable product name |
| `units` | Number of units sold (net fulfilled) |
| `selling_price` | Per‑unit selling price (₹) |
| `unit_cost` | Per‑unit cost of goods (₹) |
| `platform_fee` | Total platform fee for the line (₹) |
| `shipping_cost` | Total shipping cost for the line (₹) |
| `ad_cost` | Total advertising cost for the line (₹) |
| `refund_amount` | Total refund amount for the line (₹) |

**Important:** No column may be omitted. Missing values are reported as validation errors; they are **not** silently filled.

A downloadable CSV template is provided in the UI.

## Core Calculations (see `src/analytics.py`)

- **Gross sales**: `units * selling_price`
- **Revenue (net sales)**: `gross_sales - refund_amount`
- **Cost of goods**: `units * unit_cost`
- **Estimated contribution profit**: `revenue - cost_of_goods - platform_fee - shipping_cost - ad_cost`
- **Profit margin %**: `estimated_profit / revenue * 100` (undefined when revenue = 0)
- **AOV**: `total net revenue / number of unique orders`

All aggregations (by SKU, marketplace, date) use the summed values of the line‑level metrics.

## Running Tests

The test suite validates the calculation logic and edge‑cases.

```bash
pytest -q
```

All tests should pass. If you add new functionality, extend the tests accordingly.

## Limitations & Future Enhancements

- No authentication – suitable for internal use only.
- Data is kept in memory; large files may impact performance.
- Marketplace‑specific adapters, inventory forecasting, automated email reports, and multi‑user deployment are planned (see the *Future Roadmap* section in the original spec).

## License

This project is provided for educational and internal prototyping purposes. Feel free to adapt and extend it for your own needs.
