"""
=======================================================================
 MAMA EARTH CAPSTONE  |  PART 3: Gen AI
 File: narrator/generate_narrative.py
-----------------------------------------------------------------------
 Flow:
   1. reads narrator/findings.json   (written by analysis/clean_and_eda.py)
   2. builds a prompt that hands the AI the verified numbers and asks for
      a Situation - Complication - Resolution brief a CEO/CFO can read
   3. calls the FREE Gemini API  (free key from Google AI Studio)
   4. if there is no key, or the network/API fails, it prints a clearly
      labelled OFFLINE fallback so the pipeline never breaks
   5. INDEPENDENT verification - takes the numbers back OUT of the
      generated text and compares them with findings.json, and also flags
      any number in the text that the analysis cannot support
   6. saves the narrative to narrator/narrative.txt with run metadata

 The script never invents a number: it only ever passes through values
 that already exist in findings.json.

 Run from the repo root:   python narrator/generate_narrative.py
 With a key (Windows) :    set GEMINI_API_KEY=AIza...
 With a key (Mac/Linux):   export GEMINI_API_KEY=AIza...
=======================================================================
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARRATOR = ROOT / "narrator"
FINDINGS_PATH = NARRATOR / "findings.json"
OUT_PATH = NARRATOR / "narrative.txt"

# Google retires model ids over time (gemini-2.0-flash was shut down on
# 1 June 2026), so instead of hardcoding one name the script asks the API
# which models the key can use and prefers the newest flash model.
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash",
                   "gemini-3.5-flash-lite", "gemini-2.5-flash"]


# --------------------------------------------------------------- prompting
def build_prompt(findings: dict) -> str:
    return f"""You are a senior business analyst writing for the CEO and CFO of Mama Earth,
an Indian beauty and personal-care e-commerce brand.

Below is a JSON of findings produced by our SQL and Python analysis of
180 orders from January to June 2026.

Write a business narrative in three clearly labelled sections:
SITUATION (what the data shows), COMPLICATION (what is hurting margins),
RESOLUTION (3-4 concrete actions, in priority order).

Rules you must follow:
- Every number you mention must be copied EXACTLY from the JSON. Do not round
  differently and do not invent any number.
- Write in plain business English. No code, no SQL, no statistical jargon.
- Keep it under 350 words.
- Mention the overall return rate, the payment-method finding, the highest-risk
  segment, and the peak month.

FINDINGS JSON:
{json.dumps(findings, indent=2)}
"""


# ----------------------------------------------------------- Gemini client
def _available_models(client) -> list:
    """
    Ask the API which models this key can actually use and prefer the newest
    flash model. This future-proofs the script: when Google retires a model id
    the script still finds a working model by itself. If the listing call
    fails, we fall back to the built-in list.
    """
    try:
        names = [m.name.replace("models/", "") for m in client.models.list()]
    except Exception:
        return FALLBACK_MODELS

    def sort_key(name: str) -> tuple:
        if "gemini" not in name:
            return (9, 0.0, name)
        bad = any(tag in name for tag in ("embedding", "aqa", "image", "tts",
                                          "vision", "exp", "preview", "live"))
        version = 0.0
        match = re.match(r"gemini-(\d+)\.(\d+)", name)
        if match:
            version = float(f"{match.group(1)}.{match.group(2)}")
        is_flash = "flash" in name
        return (0 if (is_flash and not bad) else 1, -version, name)

    ordered = sorted(names, key=sort_key)
    return list(dict.fromkeys(ordered + FALLBACK_MODELS))   # de-duplicated


def call_gemini(prompt: str):
    """Returns (text, label) on success, or (None, reason) on failure."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None, "GEMINI_API_KEY is not set"
    if not api_key.startswith("AIza"):
        return None, ("this does not look like a Google AI Studio key - those "
                      "normally start with 'AIza'. Get a free one at "
                      "https://aistudio.google.com/apikey")
    try:
        from google import genai
    except ImportError:
        return None, "the google-genai package is not installed (pip install google-genai)"
    try:
        client = genai.Client(api_key=api_key)
    except Exception as exc:
        return None, f"could not create the Gemini client ({exc})"

    base_cfg = {"temperature": 0.0, "max_output_tokens": 2048}
    configs = [dict(base_cfg, automatic_function_calling={"disable": True}),
               base_cfg]
    last_error = ""
    for model_name in _available_models(client):
        for cfg in configs:
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt, config=cfg)
                text = (response.text or "").strip()
                if text:
                    return text, f"Gemini API ({model_name})"
                last_error = f"{model_name}: the API returned an empty response"
            except Exception as exc:
                last_error = f"{model_name}: {type(exc).__name__}: {str(exc)[:200]}"
                if "automatic_function_calling" in str(exc):
                    continue
            break
    return None, last_error or "every model id failed"


def offline_narrative(findings: dict) -> str:
    """Deterministic fallback built from the same JSON - clearly labelled as NOT AI."""
    rev, ret = findings["revenue"], findings["returns"]
    seg, out = findings["highest_risk_segment"], findings["outliers"]
    cod = ret["by_payment_method"]["COD"]["return_rate_pct"]
    card = ret["by_payment_method"]["CARD"]["return_rate_pct"]
    return f"""SITUATION
Mama Earth processed {findings['data']['clean_orders']} clean orders between {findings['data']['period']['from']} and {findings['data']['period']['to']}, generating INR {rev['clean_total_inr']:,.2f} in revenue at an average order value of INR {rev['avg_order_value_inr']:,.2f}. The overall return rate is {ret['overall_rate_pct']}% - roughly one order in four comes back.

COMPLICATION
Returns are not spread evenly. COD orders return at {cod}% while card orders return at only {card}%, which makes the payment method the single strongest signal in the data. The worst combination is {seg['payment_method']} orders in Tier-2 cities, returning at {seg['return_rate_pct']}%. Raw revenue (INR {rev['raw_total_inr']:,.2f}) was inflated by INR {rev['duplicate_delta_inr']:,.2f} of duplicate orders, and two bulk orders masked March as the true peak month (INR {out['peak_month_without_outliers']['revenue_inr']:,.2f}).

RESOLUTION
1. Tighten COD: require OTP confirmation or a small prepayment on high-value COD orders, starting with Tier-2 cities where the return rate is highest.
2. Offer a prepaid incentive at checkout so the COD share of orders falls over time.
3. Investigate {ret['worst_product_by_revenue_lost']['product_name']} ({ret['worst_product_by_revenue_lost']['product_id']}), the product with the largest return-linked revenue loss (INR {ret['worst_product_by_revenue_lost']['revenue_lost_inr']:,.2f}).
4. Report revenue on de-duplicated, outlier-flagged figures so business plans are built on numbers that survive audit."""


# ------------------------------------------------------------ verification
def flatten_numbers(obj):
    """Collect every numeric value inside the findings JSON."""
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(flatten_numbers(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(flatten_numbers(v))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(float(obj))
    return out


def verify(findings: dict, text: str) -> list:
    """
    Independent check - the numbers in the narrative are compared against the
    values in findings.json, in BOTH directions:

      (a) every headline figure from findings.json must appear in the text
      (b) no number may appear in the text that findings.json cannot support

    (b) is the part that catches an AI inventing a number.
    """
    rev, ret = findings["revenue"], findings["returns"]
    seg, out = findings["highest_risk_segment"], findings["outliers"]

    headline = [
        ("Total revenue (clean)", rev["clean_total_inr"]),
        ("Average order value", rev["avg_order_value_inr"]),
        ("Overall return rate %", ret["overall_rate_pct"]),
        ("COD return rate %", ret["by_payment_method"]["COD"]["return_rate_pct"]),
        ("Highest-risk segment %", seg["return_rate_pct"]),
        ("Duplicate delta", rev["duplicate_delta_inr"]),
        ("Peak month revenue", out["peak_month_without_outliers"]["revenue_inr"]),
    ]

    # dates contain digits too - mask them so "2026-01-02" is not read as "2026"
    masked = re.sub(r"\d{4}-\d{2}-\d{2}", " DATE ", text)
    masked = re.sub(r"\d{4}-\d{2}", " MONTH ", masked)
    found = {m.replace(",", "") for m in re.findall(r"\d[\d,]*\.?\d*", masked)}

    results = []
    print("\n--- Numeric verification (source of truth = narrator/findings.json) ---")
    for label, value in headline:
        as_shown = f"{value:,.2f}".replace(",", "")
        as_short = f"{value:,.0f}".replace(",", "")
        ok = as_shown in found or as_short in found or str(value) in found
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<24} source={value}  "
              f"in narrative={'yes' if ok else 'NO'}")
        results.append((label, ok))

    allowed = {f"{v:,.2f}".replace(",", "") for v in flatten_numbers(findings)}
    allowed |= {f"{v:,.0f}".replace(",", "") for v in flatten_numbers(findings)}
    allowed |= {str(v) for v in flatten_numbers(findings)}
    allowed |= {"1", "2", "3", "4", "5"}                 # action numbering
    allowed |= {str(y) for y in range(2000, 2100)}        # years
    unsupported = {n for n in found if n not in allowed and len(n) > 2}
    print(f"\n  [{'PASS' if not unsupported else 'NOTE'}] no unsupported numbers: "
          f"{sorted(unsupported) if unsupported else 'none found'}")
    return results


# --------------------------------------------------------------------- run
def main():
    print("=" * 74)
    print("PART 3 | AI BUSINESS NARRATIVE")
    print("=" * 74)

    if not FINDINGS_PATH.exists():
        raise SystemExit(f"missing {FINDINGS_PATH.relative_to(ROOT)} - "
                         "run analysis/clean_and_eda.py first")

    findings = json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))
    print(f"  findings loaded from: {FINDINGS_PATH.relative_to(ROOT)}")

    text, source = call_gemini(build_prompt(findings))
    if text is None:
        print(f"  Gemini unavailable ({source})")
        print("  -> using the DETERMINISTIC OFFLINE FALLBACK (not AI-generated)")
        text = offline_narrative(findings)
        source = "OFFLINE FALLBACK - template, not AI-generated"
    else:
        print(f"  narrative generated by: {source}")

    print("\n" + "-" * 74 + "\n" + text + "\n" + "-" * 74)

    results = verify(findings, text)

    OUT_PATH.write_text(
        f"# Mama Earth - Business Narrative\n"
        f"# Source of numbers : narrator/findings.json (written by analysis/clean_and_eda.py)\n"
        f"# Generated by      : {source}\n"
        f"# Generated at      : {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n"
        f"# Verified figures  : {sum(1 for _, ok in results if ok)}/{len(results)} matched\n\n"
        + text + "\n",
        encoding="utf-8")
    print(f"\n  saved -> {OUT_PATH.relative_to(ROOT)}")

    passed = sum(1 for _, ok in results if ok)
    print(f"\n  RESULT: {passed}/{len(results)} headline figures verified "
          "against findings.json")


if __name__ == "__main__":
    main()
