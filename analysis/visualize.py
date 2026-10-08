"""
=======================================================================
 MAMA EARTH CAPSTONE  |  PART 2: Python
 File: analysis/visualize.py  ->  the 2 required charts
-----------------------------------------------------------------------
 Chart 1 (bar)  : return rate % by payment method
 Chart 2 (line) : monthly revenue trend, January - June 2026

 Both charts are saved into visualizations/ and then the script CHECKS
 that the files really exist on disk before it prints success - a success
 message is only worth something if there is a file to prove it.

 Cleaning is applied here too (same rules as clean_and_eda.py) so the
 charts agree with findings.json.

 Reads only the CSVs in data/ - never the SQL database.

 Run from the repo root:  python analysis/visualize.py
=======================================================================
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")            # headless-safe: no display needed to save a PNG
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "visualizations"
OUT.mkdir(exist_ok=True)

PRODUCTS_COLS = ["product_id", "product_name", "category", "price"]
ORDERS_COLS = ["order_id", "customer_id", "product_id", "order_date",
               "quantity", "discount_pct", "payment_method", "rating", "returned"]


def plain(mapping) -> dict:
    """Round + convert to plain python types, so output shows 14.71 not np.float64(14.71)."""
    return {str(k): round(float(v), 2) for k, v in mapping.items()}


def load_clean() -> pd.DataFrame:
    """Same cleaning as clean_and_eda.py, so the charts match the analysis."""
    o = pd.read_csv(DATA / "orders.csv", header=None, names=ORDERS_COLS)
    p = pd.read_csv(DATA / "products.csv", header=None, names=PRODUCTS_COLS)

    for col in ["quantity", "discount_pct", "rating", "returned"]:
        o[col] = pd.to_numeric(o[col], errors="coerce")
    p["price"] = pd.to_numeric(p["price"], errors="coerce")
    o["payment_method"] = o["payment_method"].str.strip().str.upper()
    o["discount_pct"] = o["discount_pct"].fillna(0)

    o = o.drop_duplicates(subset=["customer_id", "product_id", "order_date",
                                  "quantity", "discount_pct", "payment_method"],
                          keep="first").copy()
    m = o.merge(p, on="product_id", how="left")
    m["order_value"] = m["quantity"] * m["price"] * (1 - m["discount_pct"] / 100)
    m["order_date"] = pd.to_datetime(m["order_date"])
    m["month"] = m["order_date"].dt.to_period("M").astype(str)
    print(f"  data ready: {len(m)} orders after cleaning "
          "(duplicates removed, payment spellings normalised)")
    return m


def chart_bar(m: pd.DataFrame) -> Path:
    """Bar chart - return rate by payment method. This one chart tells the whole story."""
    rates = (m.groupby("payment_method")["returned"].mean() * 100).round(2)
    overall = 100 * m["returned"].mean()
    path = OUT / "return_rate_by_payment.png"

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(rates.index, rates.values,
                  color=["#c0392b" if v == rates.max() else "#7f8c8d" for v in rates.values])
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=11)
    ax.axhline(overall, color="grey", ls="--", lw=1,
               label=f"overall average ({overall:.1f}%)")
    ax.set_title("Return rate by payment method", fontsize=13, fontweight="bold")
    ax.set_xlabel("Payment method")
    ax.set_ylabel("Return rate (%)")
    ax.set_ylim(0, max(rates.values) * 1.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"  chart 1 saved: {path.name}")
    print(f"    {plain(rates)}   <- COD is the driver")
    return path


def chart_line(m: pd.DataFrame) -> Path:
    """Line chart - monthly revenue, so the trend is visible at a glance."""
    monthly = m.groupby("month")["order_value"].sum().round(2)
    path = OUT / "monthly_revenue_trend.png"

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly.index, monthly.values, marker="o", lw=2, color="#8e44ad")
    for x, y in zip(monthly.index, monthly.values):
        ax.annotate(f"{y:,.0f}", (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
    ax.set_title("Monthly revenue trend (January - June 2026)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (INR)")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, monthly.max() * 1.2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"  chart 2 saved: {path.name}")
    print(f"    {plain(monthly)}")
    return path


def main():
    print("=" * 74)
    print("PART 2 | VISUALISATIONS")
    print("=" * 74)
    m = load_clean()
    made = [chart_bar(m), chart_line(m)]

    # verification: a success message is worthless without files on disk
    missing = [p for p in made if not p.exists() or p.stat().st_size == 0]
    if missing:
        raise SystemExit(f"FAILED: these charts were not written: {missing}")
    print(f"\n  verified on disk: {len(made)} non-empty PNG files in visualizations/")
    for p in made:
        print(f"    {p.relative_to(ROOT)}  ({p.stat().st_size:,} bytes)")
    print("DONE | 2 charts generated and verified.")


if __name__ == "__main__":
    main()
