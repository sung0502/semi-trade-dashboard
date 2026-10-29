"""Print figures to check by hand against Census published tables (plan step 7).

Usage:
    python src/verify.py                                   # annual totals by flow and HS code
    python src/verify.py --spot "Taiwan" 2024-06 imports 8542   # one country-month value

Compare the annual totals with USA Trade Online (https://usatrade.census.gov/) or the
annual FT900 release, and record the outcome in NOTES.md.
"""
import argparse
from pathlib import Path

import pandas as pd

from config import PROCESSED_DIR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--spot", nargs=4, metavar=("COUNTRY", "MONTH", "FLOW", "HS"))
    args = parser.parse_args()

    df = pd.read_csv(args.data_dir / "trade_monthly.csv", dtype={"hs": str})
    if args.spot:
        country, month, flow, hs = args.spot
        hit = df[(df["country"] == country) & (df["month"] == month) & (df["flow"] == flow) & (df["hs"] == hs)]
        print(hit.to_string(index=False) if len(hit) else "No matching row.")
        return

    df["year"] = df["month"].str[:4].astype(int)
    annual = df.groupby(["flow", "hs", "year"]).agg(value=("value", "sum"), months=("month", "nunique"))
    annual["value_usd_millions"] = (annual.pop("value") / 1e6).round(1)
    out = args.data_dir / "verify_annual_totals.csv"
    annual.to_csv(out)
    pd.set_option("display.width", 120)
    print(annual.to_string())
    print(f"\nWrote {out}. Years with months < 12 are partial.")


if __name__ == "__main__":
    main()
