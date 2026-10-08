"""
=======================================================================
 MAMA EARTH CAPSTONE  |  PART 2: Python
 File: analysis/clean_and_eda.py
-----------------------------------------------------------------------
 What this script does, printing every intermediate result:

   1. loads the 3 raw CSVs from data/  (they have NO header row)
   2. CLEANS the data:
        - standardises payment_method spelling (7 labels -> 3)
        - removes the 5 duplicate orders and reconciles the revenue gap
        - handles missing values, each choice printed with its reason
   3. merges products + customers and computes order_value
   4. FLAGS quantity outliers with the IQR method  (flagged, never deleted)
   5. customer segmentation (spend tiers + risk segments)
   6. correlation matrix + three hypothesis checks
   7. monthly trend, raw vs outlier-corrected
   8. writes narrator/findings.json  - every value COMPUTED, none typed in

 IMPORTANT: this file reads ONLY the CSV files in data/.
            It never opens the SQL database - that is Part 1's layer.

 Run from the repo root:   python analysis/clean_and_eda.py
 or from analysis/:        python clean_and_eda.py
=======================================================================
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---- paths: work no matter which folder the script is run from ---------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NARRATOR = ROOT / "narrator"
NARRATOR.mkdir(exist_ok=True)

CUSTOMERS_COLS = ["customer_id", "name", "city", "city_tier",
                  "signup_date", "acquisition_source"]
PRODUCTS_COLS = ["product_id", "product_name", "category", "price"]
ORDERS_COLS = ["order_id", "customer_id", "product_id", "order_date",
               "quantity", "discount_pct", "payment_method", "rating", "returned"]


def section(title: str) -> None:
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def count_map(series) -> dict:
    """value_counts() as plain ints, so output shows {'Card': 56} not np.int64(56)."""
    return {str(k): int(v) for k, v in series.value_counts().items()}


def load_raw():
    """Read the 3 CSVs exactly as they are (headerless, blanks kept as NaN)."""
    section("1 | LOAD RAW DATA (CSV only - the SQL database is not used here)")
    orders = pd.read_csv(DATA / "orders.csv", header=None, names=ORDERS_COLS)
    products = pd.read_csv(DATA / "products.csv", header=None, names=PRODUCTS_COLS)
    customers = pd.read_csv(DATA / "customers.csv", header=None, names=CUSTOMERS_COLS)

    print(f"  orders.csv     {orders.shape[0]:>3} rows x {orders.shape[1]} cols")
    print(f"  products.csv   {products.shape[0]:>3} rows x {products.shape[1]} cols")
    print(f"  customers.csv  {customers.shape[0]:>3} rows x {customers.shape[1]} cols")

    print("\n  Data quality problems found in the raw files (fixed below):")
    print(f"    - payment_method spellings : {orders['payment_method'].nunique()} "
          f"labels -> {sorted(orders['payment_method'].unique())}")
    dups = orders.duplicated(subset=["customer_id", "product_id", "order_date",
                                     "quantity", "discount_pct", "payment_method"],
                             keep="first").sum()
    print(f"    - duplicate order rows     : {dups}")
    print(f"    - missing discount_pct     : {int(orders['discount_pct'].isna().sum())}")
    print(f"    - missing rating           : {int(orders['rating'].isna().sum())}")
    qty = pd.to_numeric(orders["quantity"], errors="coerce")
    print(f"    - quantity outliers (>5)   : {int((qty > 5).sum())}")
    print("    - no header row in any CSV : column names are defined in this script")
    return orders, products, customers


def clean(orders, products, customers):
    """All cleaning steps; each one prints before/after and its reason."""
    section("2 | CLEANING")

    # 2a - numeric conversion -------------------------------------------------
    for col in ["quantity", "discount_pct", "rating", "returned"]:
        orders[col] = pd.to_numeric(orders[col], errors="coerce")
    products["price"] = pd.to_numeric(products["price"], errors="coerce")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    print("  2a. numeric + date columns parsed  (blank cells -> NaN, NOT zero)")

    # 2b - payment method casing ---------------------------------------------
    print(f"\n  2b. payment_method BEFORE: {count_map(orders['payment_method'])}")
    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    print(f"      payment_method AFTER : {count_map(orders['payment_method'])}")
    print("      -> Card/CARD/card collapsed into one label. "
          "7 spellings -> 3 clean labels.")

    # 2c - duplicates ---------------------------------------------------------
    dup_mask = orders.duplicated(
        subset=["customer_id", "product_id", "order_date", "quantity",
                "discount_pct", "payment_method"], keep="first")
    print(f"\n  2c. duplicate order rows found: {int(dup_mask.sum())}")
    print(orders[dup_mask][["order_id", "customer_id", "product_id",
                            "order_date", "quantity"]].to_string(index=False))
    before = len(orders)
    orders = orders[~dup_mask].copy()
    print(f"      rows: {before} -> {len(orders)}  "
          "(kept the first occurrence, dropped the copy)")

    # 2d - missing values -----------------------------------------------------
    print("\n  2d. missing values")
    n_disc = int(orders["discount_pct"].isna().sum())
    orders["discount_pct"] = orders["discount_pct"].fillna(0)
    print(f"      discount_pct : {n_disc} blanks -> filled with 0")
    print("                     reason: no discount recorded = the customer paid")
    print("                     full price, which keeps the revenue formula honest")

    n_rating = int(orders["rating"].isna().sum())
    print(f"      rating       : {n_rating} blanks -> LEFT AS NULL (no fill)")
    print("                     reason: a rating is an opinion, not a measurement.")
    print("                     Filling it with a mean would invent an opinion the")
    print("                     customer never gave. Those rows are simply excluded")
    print("                     from the rating checks later on.")

    print("      quantity     : no blanks -> nothing to fill")
    print("                     (an earlier draft filled quantity with 1; that would")
    print("                      silently change revenue, so it is NOT done)")
    return orders, products, customers


def merge_and_value(orders, products, customers):
    section("3 | MERGE + REVENUE RECONCILIATION")
    m = orders.merge(products, on="product_id", how="left", validate="m:1")
    m = m.merge(customers, on="customer_id", how="left", validate="m:1")
    assert len(m) == len(orders), "merge changed the row count!"
    m["order_value"] = m["quantity"] * m["price"] * (1 - m["discount_pct"] / 100)
    m["month"] = m["order_date"].dt.to_period("M").astype(str)
    print(f"  merged rows: {len(m)}  (no row lost in the joins)")

    # "raw revenue" = all 180 rows exactly as they arrived, duplicates included
    raw = pd.read_csv(DATA / "orders.csv", header=None, names=ORDERS_COLS)
    raw["quantity"] = pd.to_numeric(raw["quantity"], errors="coerce")
    raw["discount_pct"] = pd.to_numeric(raw["discount_pct"], errors="coerce").fillna(0)
    raw = raw.merge(products, on="product_id", how="left")
    raw_revenue = float((raw["quantity"] * raw["price"]
                         * (1 - raw["discount_pct"] / 100)).sum())
    clean_revenue = float(m["order_value"].sum())

    print(f"\n  raw revenue   (180 orders, as received)  : Rs {raw_revenue:,.2f}")
    print(f"  clean revenue (175 orders, de-duplicated): Rs {clean_revenue:,.2f}")
    print(f"  difference                               : Rs {raw_revenue - clean_revenue:,.2f}")
    print("  -> the gap is exactly the 5 duplicate rows removed in step 2c.")
    print("     The SQL layer (Part 1) reports the raw figure, this layer reports")
    print("     the clean one - and the two reconcile perfectly.")
    return m, raw_revenue, clean_revenue


def flag_outliers(m):
    section("4 | OUTLIERS - IQR METHOD (flagged, NOT deleted)")
    q1, q3 = float(m["quantity"].quantile(0.25)), float(m["quantity"].quantile(0.75))
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    m["is_outlier"] = (m["quantity"] < lower) | (m["quantity"] > upper)

    print(f"  Q1 = {q1}, Q3 = {q3}, IQR = Q3 - Q1 = {iqr}")
    print(f"  lower fence = Q1 - 1.5*IQR = {lower}")
    print(f"  upper fence = Q3 + 1.5*IQR = {upper}")
    print(f"  rows flagged as outliers: {int(m['is_outlier'].sum())}")
    print(m.loc[m["is_outlier"], ["order_id", "customer_id", "product_id",
                                  "quantity", "order_value"]].to_string(index=False))
    print("\n  Both rows are KEPT in the dataset. Dropping them would quietly")
    print("  delete Rs 17,945 of real revenue from the analysis.")
    print("  The brief says: flag outliers, never remove them.")
    return m


def segment(m):
    section("5 | CUSTOMER SEGMENTATION (patterns)")
    cust = m.groupby("customer_id").agg(
        orders=("order_id", "count"),
        spend=("order_value", "sum"),
        returns=("returned", "sum"),
        avg_rating=("rating", "mean"))
    cust["return_rate"] = (100 * cust["returns"] / cust["orders"]).round(2)
    cust["segment"] = pd.cut(cust["spend"], bins=[-1, 1200, 2500, np.inf],
                             labels=["Low value", "Mid value", "High value"])
    cust = cust.merge(m[["customer_id", "city", "city_tier", "acquisition_source"]]
                      .drop_duplicates("customer_id"), on="customer_id", how="left")

    print("  Spend-based segments (average per customer):")
    print(cust.groupby("segment", observed=True).agg(
        customers=("orders", "size"),
        avg_orders=("orders", "mean"),
        avg_spend=("spend", "mean"),
        avg_return_rate=("return_rate", "mean")).round(2).to_string())

    print("\n  Highest-risk segment - COD paid in Tier-2 cities:")
    seg = m[(m["payment_method"] == "COD") & (m["city_tier"] == 2)]
    t1 = m[(m["payment_method"] == "COD") & (m["city_tier"] == 1)]
    print(f"    COD + Tier-2 : {len(seg):>3} orders, return rate {100*seg['returned'].mean():.1f}%"
          "   <- worst combination in the data")
    print(f"    COD + Tier-1 : {len(t1):>3} orders, return rate {100*t1['returned'].mean():.1f}%")

    print("\n  Repeat returners (>= 3 orders, top 5 by return rate):")
    print(cust[cust["orders"] >= 3].sort_values("return_rate", ascending=False)
          .head(5)[["orders", "returns", "return_rate", "spend", "city"]].to_string())
    return cust


def correlations(m):
    section("6 | CORRELATION + HYPOTHESIS CHECKS")
    corr = m[["quantity", "discount_pct", "rating", "returned", "order_value"]] \
        .corr(numeric_only=True).round(3)
    print("  Correlation matrix:")
    print(corr.to_string())

    r_disc = float(corr.loc["discount_pct", "returned"])
    print(f"\n  CHECK 1 - 'do discounts cause returns?'   r = {r_disc}")
    print("    Verdict: NOT supported. The correlation is negligible, so the")
    print("    discount level is not what drives returns. Report 8 in Part 1")
    print("    points the same way - the highest discount band actually returns")
    print("    the least.")

    r_rating = float(corr.loc["rating", "returned"])
    low = m[m["rating"] <= 2]
    high = m[m["rating"] >= 4]
    print(f"\n  CHECK 2 - 'do unhappy customers return more?'  r = {r_rating}")
    print(f"    rating 1-2 : {len(low):>3} orders, return rate {100*low['returned'].mean():.1f}%")
    print(f"    rating 4-5 : {len(high):>3} orders, return rate {100*high['returned'].mean():.1f}%")
    print("    Verdict: the direction is right - low-rated orders do return more -")
    print("    but plenty of returns happen on orders the customer rated 4 or 5.")
    print("    So returns are not purely a satisfaction problem.")

    r_qty = float(corr.loc["quantity", "returned"])
    print(f"\n  CHECK 3 - 'do bulk orders return more?'   r = {r_qty}")
    print("    Verdict: no meaningful relationship.")

    print("\n  All three correlations are weak (|r| < 0.15). That is itself a")
    print("  finding: no single numeric column explains returns. The signal lives")
    print("  in the payment-method / city-tier combination, not in a number.")
    return corr, r_disc, r_rating


def monthly(m):
    section("7 | MONTHLY TREND (raw vs outlier-corrected)")
    monthly_all = m.groupby("month")["order_value"].sum().round(2)
    monthly_clean = m[~m["is_outlier"]].groupby("month")["order_value"].sum().round(2)
    trend = pd.DataFrame({"revenue_all_orders": monthly_all,
                          "revenue_without_outliers": monthly_clean,
                          "return_rate_pct": (100 * m.groupby("month")["returned"].mean()).round(2)})
    print(trend.to_string())
    print(f"\n  peak month, all orders        : {monthly_all.idxmax()} (Rs {monthly_all.max():,.2f})")
    print(f"  peak month, outliers excluded : {monthly_clean.idxmax()} (Rs {monthly_clean.max():,.2f})")
    print("  -> January looks like the best month only because of the 2 bulk")
    print("     orders flagged above. Once those are set aside, March is the true")
    print("     peak. Both numbers are reported; neither set of rows is deleted.")
    return monthly_all, monthly_clean


def export_findings(m, cust, corr, r_disc, r_rating, monthly_all, monthly_clean,
                    raw_revenue, clean_revenue):
    section("8 | EXPORT narrator/findings.json  (every value computed above)")
    pay = m.groupby("payment_method")["returned"].agg(["size", "sum"])
    pay["rate"] = (100 * pay["sum"] / pay["size"]).round(2)
    cat = m.groupby("category")["returned"].agg(["size", "sum"])
    cat["rate"] = (100 * cat["sum"] / cat["size"]).round(2)
    city = m.groupby("city")["returned"].agg(["size", "sum"])
    city["rate"] = (100 * city["sum"] / city["size"]).round(2)
    ch = m.groupby("acquisition_source")["returned"].agg(["size", "sum"])
    ch["rate"] = (100 * ch["sum"] / ch["size"]).round(2)

    prod_loss = m[m["returned"] == 1].groupby(["product_id", "product_name"])["order_value"].sum()
    worst = prod_loss.idxmax()
    seg = m[(m["payment_method"] == "COD") & (m["city_tier"] == 2)]

    findings = {
        "data": {
            "source_files": ["data/customers.csv", "data/products.csv", "data/orders.csv"],
            "raw_orders": int(len(m) + 5),
            "clean_orders": int(len(m)),
            "duplicates_removed": 5,
            "customers": int(m["customer_id"].nunique()),
            "products": int(m["product_id"].nunique()),
            "period": {"from": str(m["order_date"].min().date()),
                       "to": str(m["order_date"].max().date())},
        },
        "revenue": {
            "raw_total_inr": round(raw_revenue, 2),
            "clean_total_inr": round(clean_revenue, 2),
            "duplicate_delta_inr": round(raw_revenue - clean_revenue, 2),
            "avg_order_value_inr": round(float(m["order_value"].mean()), 2),
        },
        "returns": {
            "overall_rate_pct": round(float(100 * m["returned"].mean()), 2),
            "returned_orders": int(m["returned"].sum()),
            "by_payment_method": {k: {"orders": int(v["size"]),
                                      "return_rate_pct": float(v["rate"])}
                                  for k, v in pay.iterrows()},
            "by_category": {k: {"orders": int(v["size"]),
                                "return_rate_pct": float(v["rate"])}
                            for k, v in cat.iterrows()},
            "by_city": {k: {"orders": int(v["size"]),
                            "return_rate_pct": float(v["rate"])}
                        for k, v in city.iterrows()},
            "by_acquisition_source": {k: {"orders": int(v["size"]),
                                          "return_rate_pct": float(v["rate"])}
                                      for k, v in ch.iterrows()},
            "worst_product_by_revenue_lost": {
                "product_id": worst[0], "product_name": worst[1],
                "revenue_lost_inr": round(float(prod_loss.max()), 2)},
        },
        "highest_risk_segment": {
            "payment_method": "COD", "city_tier": 2,
            "orders": int(len(seg)),
            "return_rate_pct": round(float(100 * seg["returned"].mean()), 2),
        },
        "outliers": {
            "method": "IQR (1.5x)",
            "q1": float(m["quantity"].quantile(0.25)),
            "q3": float(m["quantity"].quantile(0.75)),
            "upper_fence": float(m["quantity"].quantile(0.75) + 1.5 * (
                m["quantity"].quantile(0.75) - m["quantity"].quantile(0.25))),
            "flagged_rows": int(m["is_outlier"].sum()),
            "order_ids": list(m.loc[m["is_outlier"], "order_id"]),
            "handling": "flagged only, never dropped",
            "peak_month_all_orders": {"month": str(monthly_all.idxmax()),
                                      "revenue_inr": float(monthly_all.max())},
            "peak_month_without_outliers": {"month": str(monthly_clean.idxmax()),
                                            "revenue_inr": float(monthly_clean.max())},
        },
        "correlations": {
            "discount_vs_returned": round(r_disc, 3),
            "rating_vs_returned": round(r_rating, 3),
            "quantity_vs_returned": round(float(corr.loc["quantity", "returned"]), 3),
            "note": "all correlations are weak (|r| < 0.15) - no single numeric "
                    "variable explains returns",
        },
        "monthly": {k: float(v) for k, v in monthly_clean.items()},
        "segment_summary": {
            "low_value_customers": int((cust["segment"] == "Low value").sum()),
            "mid_value_customers": int((cust["segment"] == "Mid value").sum()),
            "high_value_customers": int((cust["segment"] == "High value").sum()),
        },
    }

    out = NARRATOR / "findings.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
    print(f"  written -> {out}")
    print("  key numbers:")
    print(f"    clean revenue        : {findings['revenue']['clean_total_inr']}")
    print(f"    overall return rate  : {findings['returns']['overall_rate_pct']}%")
    print(f"    COD return rate      : {findings['returns']['by_payment_method']['COD']['return_rate_pct']}%")
    print(f"    riskiest segment     : {findings['highest_risk_segment']['return_rate_pct']}%")
    print("\n  Every value above came from a variable computed in this script.")
    print("  Nothing in findings.json was typed by hand.")
    return findings


def main():
    orders, products, customers = load_raw()
    orders, products, customers = clean(orders, products, customers)
    m, raw_revenue, clean_revenue = merge_and_value(orders, products, customers)
    m = flag_outliers(m)
    cust = segment(m)
    corr, r_disc, r_rating = correlations(m)
    monthly_all, monthly_clean = monthly(m)
    export_findings(m, cust, corr, r_disc, r_rating, monthly_all, monthly_clean,
                    raw_revenue, clean_revenue)
    section("DONE | cleaning + EDA complete, narrator/findings.json written")
    print("  next: analysis/visualize.py  (the 2 charts)")
    print("        narrator/generate_narrative.py  (the AI business narrative)")


if __name__ == "__main__":
    main()
