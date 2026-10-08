# Mama Earth — Returns & Growth Intelligence Pipeline

**Business problem.** Mama Earth's profit margins are being eaten by product returns, but the
company does not know *where* the returns are actually coming from. This project answers that
with a three-layer pipeline over **45 customers, 16 products and 180 orders** (Jan–Jun 2026).

| Layer | What it does | Output |
|---|---|---|
| **1. SQL** | schema + constraints, loads the raw data, 9 business reports | `sql/schema.sql`, `sql/seed_data.sql`, `sql/reports.sql` |
| **2. Python** | cleaning, IQR outlier flagging, segmentation, correlations, 2 charts | `analysis/clean_and_eda.py`, `analysis/visualize.py`, `visualizations/` |
| **3. Gen AI** | turns the verified findings into a CEO/CFO narrative | `narrator/generate_narrative.py`, `narrator/findings.json` |

> **The rule this project is built on:** no layer reports a number it did not itself compute or
> receive from the layer before it. `narrator/findings.json` is written *entirely* by
> `analysis/clean_and_eda.py` — not a single value in it is typed by hand.

---

## Headline findings

| Finding | Number |
|---|---|
| Recorded return rate | **25.0%** on raw data, **25.14%** on cleaned data — about 1 order in 4 comes back |
| Raw vs clean revenue | **₹99,860.20 → ₹97,358.30**; the ₹2,501.90 gap is exactly the 5 duplicate rows |
| **COD return rate** (the main driver) | **44.44%** vs CARD **14.71%** and UPI **18.87%** |
| Highest-risk segment | **COD paid in Tier-2 cities: 54.55%** (COD + Tier-1: 37.5%) |
| Highest-return category | Skincare 31.67% → Haircare 25.93% → Babycare 23.33% → PersonalCare 13.89% |
| Worst city | Jaipur 42.11% (Lucknow 30.61%, Mumbai 17.86%) |
| Worst channel | Ad 32.08% return rate *and* the highest revenue — an expensive combination |
| Costliest product by returns | **P11 Milky Soft Baby Lotion — ₹8,073 lost** to returns |
| Peak month | **March ₹20,318.90** once the 2 bulk orders are set aside; January's ₹29,582 was inflated by them |
| Correlations | all weak (\|r\| < 0.15) — discounts do **not** drive returns (r = −0.088) |

**One-line story:** returns are not a product-quality problem, they are a **COD problem** — and it
gets worse in Tier-2 cities. Fixing COD (OTP confirmation / prepaid incentive) attacks the single
largest driver of margin loss.

---

## Repository structure

```
capstone-project-krishna-sharma/
├── README.md                      this file
├── sql/
│   ├── schema.sql                 tables + PRIMARY KEY / FOREIGN KEY / NOT NULL / CHECK
│   ├── seed_data.sql              loads the raw data (generated from data/*.csv by code)
│   └── reports.sql                the 9 business reports, each with its actual output
├── data/
│   ├── customers.csv              45 rows  (never hand-edited)
│   ├── products.csv               16 rows  (never hand-edited)
│   └── orders.csv                 180 rows (never hand-edited)
├── analysis/
│   ├── clean_and_eda.py           cleaning + IQR outliers + segmentation + correlations
│   └── visualize.py               the 2 charts, saved and then verified on disk
├── visualizations/
│   ├── return_rate_by_payment.png bar chart — the COD finding in one picture
│   └── monthly_revenue_trend.png  line chart — revenue Jan–Jun 2026
└── narrator/
    ├── findings.json              written by clean_and_eda.py, never hand-typed
    └── generate_narrative.py      Gemini API call + independent numeric verification
```

---

## How to run

### Part 1 — SQL

Run the three files in order. They work in any SQLite client, or straight from the shell:

```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 -header -column mamaearth.db < sql/reports.sql
```

- `schema.sql` creates the tables with the constraints.
- `seed_data.sql` inserts all 241 rows and **ends with 5 verification queries** (row counts,
  foreign-key check, NULL counts, the messy `payment_method` values, and the 25% return split).
- `reports.sql` holds the 9 business reports; each one has its **actual output pasted above it**
  as a comment, so a marker can compare their run against mine instantly.

Both schema and seed file open with `PRAGMA foreign_keys = ON;` — SQLite has foreign-key
enforcement **off** by default, and without that line the `FOREIGN KEY` clauses would be
decorative.

### Part 2 — Python (cleaning, EDA, charts)

```bash
python analysis/clean_and_eda.py     # cleans + analyses, writes narrator/findings.json
python analysis/visualize.py         # writes the 2 charts into visualizations/
```

Both scripts read **only** the CSVs in `data/` — they never open the SQL database, per the brief.
Every cleaning decision is printed with its reason, and `visualize.py` checks the PNG files
really exist before it reports success.

### Part 3 — Gen AI narrative

```bash
# free key from https://aistudio.google.com/apikey
export GEMINI_API_KEY="AIza..."      # Windows:  set GEMINI_API_KEY=AIza...
python narrator/generate_narrative.py
```

Without a key the script prints a **clearly labelled** offline fallback instead of failing, so the
pipeline can be demonstrated anywhere. It never presents the template as AI output.

The script asks the API which models the key can use and picks the newest flash model itself, so
a retired model id (like `gemini-2.0-flash`, shut down on 1 June 2026) cannot break the run.

---

## Data quality work (Part 2)

| Issue found in the raw CSVs | How it was handled |
|---|---|
| `payment_method` written 7 different ways (`Card`, `CARD`, `card`, `COD`, `cod`, `UPI`, `upi`) | normalised to 3 labels: CARD 70, UPI 55, COD 55 |
| 5 duplicate order rows (`O0176`–`O0180`) | removed, and the ₹2,501.90 revenue gap reconciled exactly |
| 12 blank `discount_pct` | filled with 0 — no discount recorded means full price was paid |
| 15 blank `rating` | **left as NULL** — a rating is an opinion; filling it would invent data |
| 2 quantity outliers (`O0011` = 25, `O0098` = 30) | **flagged with IQR (upper fence = 3.5), NOT deleted**; the outlier-corrected monthly peak is reported alongside the uncorrected one |
| No header row in any CSV | column names are defined in code (`clean_and_eda.py`, `visualize.py`) |

---

## Why the numbers can be trusted

1. **SQL layer** — row counts, `pragma_foreign_key_check` (0 violations) and NULL counts are
   printed by `seed_data.sql` every time it runs.
2. **Cross-layer reconciliation** — the SQL layer reports raw revenue ₹99,860.20; the Python
   layer reports ₹97,358.30 after removing 5 duplicates. Difference = ₹2,501.90, exactly those
   rows. Two independent layers, same story.
3. **Charts** — `visualize.py` re-checks that both PNG files exist and are non-empty before it
   prints success.
4. **Narrative** — `generate_narrative.py` pulls the numbers back out of the generated text and
   compares them with `findings.json` (7/7 headline figures PASS), and also flags any number in
   the text that the analysis cannot support.

Actual verification output:

```
--- Numeric verification (source of truth = narrator/findings.json) ---
  [PASS] Total revenue (clean)    source=97358.3   in narrative=yes
  [PASS] Average order value      source=556.33    in narrative=yes
  [PASS] Overall return rate %    source=25.14     in narrative=yes
  [PASS] COD return rate %        source=44.44     in narrative=yes
  [PASS] Highest-risk segment %   source=54.55     in narrative=yes
  [PASS] Duplicate delta          source=2501.9    in narrative=yes
  [PASS] Peak month revenue       source=20318.9   in narrative=yes
  [PASS] no unsupported numbers: none found
  RESULT: 7/7 headline figures verified against findings.json
```

---

## Recommended actions (from the narrative)

1. **Tighten COD** — OTP confirmation or a token prepayment on high-value COD orders, starting
   with Tier-2 cities where the return rate is 54.55%.
2. **Reward prepaid** — a small checkout incentive to shift the COD share downwards.
3. **Investigate P11 (Milky Soft Baby Lotion)** — the single largest return-linked revenue loss,
   ₹8,073.
4. **Report on clean figures** — plan on de-duplicated, outlier-flagged numbers so decisions
   survive an audit.

---

## Requirements

The three libraries used, with a single install command:

```bash
pip install pandas matplotlib google-genai
```

| Library | Used for | Needed? |
|---|---|---|
| `pandas` | loading and cleaning the CSVs (Part 2) | yes |
| `matplotlib` | the two charts (Part 2) | yes |
| `google-genai` | the live Gemini call (Part 3) | only for the AI narrative — without it Part 3 still runs, using the labelled offline fallback |

Python 3.9+ is required. Part 1 (SQL) needs no libraries at all — any SQLite client will do.

---

## Notes & limitations

- The raw CSVs contain no `return_reason` column, so *why* a specific order was returned cannot be
  measured. The analysis identifies **where** returns concentrate — payment method, city tier,
  category, product — not the root cause.
- All correlations are weak; that is itself a finding. Returns are not driven by a single numeric
  variable but by the COD + Tier-2 combination.
- SQLite was used as the SQL engine (file-based, no server needed) and every step is code —
  nothing was done by hand in a GUI tool.
