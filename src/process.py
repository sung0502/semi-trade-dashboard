"""Turn raw Census responses into the metrics the dashboard shows.

Usage:
    python src/process.py

Reads data/raw/*.json and data/events.csv, writes:
    data/processed/trade_monthly.csv    tidy monthly values by flow, HS code and country
    data/processed/trade_annual.csv     calendar-year values and shares by country
    data/processed/concentration_annual.csv  calendar-year total, top-3 share and HHI
    data/processed/checks.json          reconciliation of country rows against Census totals
    data/processed/dashboard_data.json  everything the HTML dashboard needs
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from config import (DERIVED, EVENT_WINDOW_MONTHS, EVENTS_CSV, FLOWS, HS_CODES, PROCESSED_DIR,
                    PRODUCTS, RAW_DIR, TOP_N)
from metrics import (annual_concentration, hhi, hhi_label, rolling_12, shares, top_k_share,
                     window_comparison)

NAME_OVERRIDES = {
    "KOREA, SOUTH": "South Korea",
    "CHINA": "China",
    "TAIWAN": "Taiwan",
    "HONG KONG": "Hong Kong",
    "UNITED KINGDOM": "United Kingdom",
    "VIETNAM": "Vietnam",
    "NETHERLANDS": "Netherlands",
}


def nice_name(raw: str) -> str:
    raw = raw.strip()
    if raw in NAME_OVERRIDES:
        return NAME_OVERRIDES[raw]
    return " ".join(w.capitalize() if len(w) > 2 or w in ("UK",) else w.lower() for w in raw.split())


def is_country(code: str) -> bool:
    """Census country codes are 4 digits >= 1000. Totals ('-'), groupings like the EU
    (0001-0099) and region totals ('4XXX') are excluded so nothing is double counted."""
    return code.isdigit() and int(code) >= 1000


def load_raw(raw_dir: Path):
    country_rows, total_rows = [], []
    for path in sorted(raw_dir.glob("*.json")):
        payload = json.loads(path.read_text())
        rows = payload.get("rows") or []
        if len(rows) < 2:
            continue
        header = rows[0]
        flow, hs = payload["flow"], payload["hs"]
        value_field = FLOWS[flow]["value_field"]
        idx = {name: i for i, name in enumerate(header)}
        for r in rows[1:]:
            code = str(r[idx["CTY_CODE"]]).strip()
            rec = {
                "flow": flow,
                "hs": hs,
                "month": str(r[idx["time"]]),
                "cty_code": code,
                "country": nice_name(str(r[idx["CTY_NAME"]])),
                "value": float(r[idx[value_field]] or 0),
            }
            if is_country(code):
                country_rows.append(rec)
            elif code == "-":
                total_rows.append(rec)
    if not country_rows:
        raise SystemExit(f"No country rows found in {raw_dir}. Run src/fetch_census.py first.")
    df = pd.DataFrame(country_rows)
    totals = pd.DataFrame(total_rows)
    return df, totals


def reconcile(df: pd.DataFrame, totals: pd.DataFrame) -> dict:
    """Sum of country rows should equal the Census all-countries total for each month."""
    if totals.empty:
        return {"status": "no total rows returned; reconciliation skipped"}
    summed = df.groupby(["flow", "hs", "month"])["value"].sum()
    official = totals.groupby(["flow", "hs", "month"])["value"].sum()
    joined = pd.concat([summed.rename("countries"), official.rename("census_total")], axis=1).dropna()
    joined["pct_diff"] = (joined["countries"] - joined["census_total"]).abs() / joined["census_total"].where(joined["census_total"] > 0)
    worst = joined["pct_diff"].max()
    return {
        "months_checked": int(len(joined)),
        "max_pct_difference": round(float(worst) * 100, 4) if pd.notna(worst) else None,
        "months_over_0.5pct": int((joined["pct_diff"] > 0.005).sum()),
        "status": "ok" if pd.notna(worst) and worst <= 0.005 else "check differences",
    }


def monthly_wide(df: pd.DataFrame, flow: str, product: str) -> pd.DataFrame:
    codes = DERIVED.get(product, [product])
    sub = df[(df["flow"] == flow) & (df["hs"].isin(codes))]
    if sub.empty:
        return pd.DataFrame()
    wide = sub.pivot_table(index="month", columns="country", values="value", aggfunc="sum")
    wide.index = pd.PeriodIndex(wide.index, freq="M")
    full = pd.period_range(wide.index.min(), wide.index.max(), freq="M")
    # Census omits country-months with no trade, so missing means zero.
    return wide.reindex(full).fillna(0.0)


def r(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


def build_view(wide: pd.DataFrame, events: pd.DataFrame, flow: str) -> dict:
    r12 = rolling_12(wide).dropna(how="all")
    sh = shares(r12)
    h = hhi(sh)
    t3 = top_k_share(sh, 3)
    months = [str(p) for p in r12.index]

    # Fixed set of named countries per view, ranked by total over the whole period,
    # so colours follow the country rather than its rank in any one month.
    top = wide.sum().sort_values(ascending=False).head(TOP_N).index.tolist()
    share_series = {c: [r(v * 100, 2) for v in sh[c]] for c in top}
    share_series["Other"] = [r(v * 100, 2) for v in sh.drop(columns=top).sum(axis=1, min_count=1)]

    latest, prior = r12.index[-1], r12.index[-1] - 12
    latest_vals = r12.loc[latest]
    latest_share = sh.loc[latest]
    has_prior = prior in r12.index
    table = []
    for c in latest_vals.sort_values(ascending=False).head(10).index:
        row = {"country": c, "value": r(latest_vals[c], 0), "share": r(latest_share[c] * 100, 2)}
        if has_prior:
            pv = r12.loc[prior, c]
            row["value_change_pct"] = r((latest_vals[c] / pv - 1) * 100, 1) if pv > 0 else None
            row["share_change_pp"] = r((latest_share[c] - sh.loc[prior, c]) * 100, 2)
        table.append(row)

    top_country = latest_vals.idxmax()
    kpis = {
        "latest_month": str(latest),
        "total_12m": r(latest_vals.sum(), 0),
        "total_12m_prior": r(r12.loc[prior].sum(), 0) if has_prior else None,
        "top_country": top_country,
        "top_share": r(latest_share[top_country] * 100, 1),
        "top3_share": r(t3.loc[latest] * 100, 1),
        "hhi": r(h.loc[latest], 0),
        "hhi_prior": r(h.loc[prior], 0) if has_prior else None,
        "hhi_label": hhi_label(h.loc[latest]),
    }

    event_results = []
    for _, ev in events.iterrows():
        res = window_comparison(wide, pd.Period(ev["date"], freq="M"), EVENT_WINDOW_MONTHS)
        if res is None:
            event_results.append({"date": ev["date"], "available": False})
            continue
        before, after = res
        b_sh, a_sh = before / before.sum(), after / after.sum()
        movers = (pd.concat([b_sh, a_sh], axis=1).max(axis=1)).sort_values(ascending=False).head(8).index
        event_results.append({
            "date": ev["date"],
            "available": True,
            "total_change_pct": r((after.sum() / before.sum() - 1) * 100, 1) if before.sum() > 0 else None,
            "countries": [
                {"country": c, "before": r(b_sh[c] * 100, 2), "after": r(a_sh[c] * 100, 2),
                 "change_pp": r((a_sh[c] - b_sh[c]) * 100, 2)}
                for c in movers
            ],
        })

    return {
        "months": months,
        "totals": [r(v, 0) for v in r12.sum(axis=1)],
        "share_series": share_series,
        "hhi": [r(v, 0) for v in h],
        "top3": [r(v * 100, 2) for v in t3],
        "table": table,
        "kpis": kpis,
        "events": event_results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=PROCESSED_DIR)
    args = parser.parse_args()

    df, totals = load_raw(args.raw_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df.sort_values(["flow", "hs", "month", "country"]).to_csv(args.out_dir / "trade_monthly.csv", index=False)

    checks = reconcile(df, totals)
    (args.out_dir / "checks.json").write_text(json.dumps(checks, indent=2))
    print("Reconciliation:", checks)

    events = pd.read_csv(EVENTS_CSV, dtype=str).fillna("")
    views, annual_rows, concentration = {}, [], []
    for flow in FLOWS:
        for product in PRODUCTS:
            wide = monthly_wide(df, flow, product)
            if wide.empty or len(wide) < 12:
                print(f"Skipping {flow}/{product}: fewer than 12 months of data")
                continue
            yearly = wide.groupby(wide.index.year).sum()
            long = yearly.stack().rename("value").reset_index()
            long.columns = ["year", "country", "value"]
            long["share"] = long["value"] / long.groupby("year")["value"].transform("sum")
            annual_rows.append(long.assign(flow=flow, product=product))
            concentration.append(annual_concentration(wide).reset_index().assign(flow=flow, product=product))
            views[f"{flow}|{product}"] = build_view(wide, events, flow)
            print(f"Built {flow}/{product}: {len(wide)} months, {wide.shape[1]} countries")

    lead = ["flow", "product"]
    annual = pd.concat(annual_rows)
    annual = annual[annual["value"] > 0]
    annual[lead + ["year", "country", "value", "share"]].to_csv(args.out_dir / "trade_annual.csv", index=False)
    conc = pd.concat(concentration)
    conc[lead + [c for c in conc.columns if c not in lead]].to_csv(
        args.out_dir / "concentration_annual.csv", index=False, float_format="%.6g")

    data = {
        "meta": {
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source": "U.S. Census Bureau, International Trade API (HS4, monthly, by country)",
            "source_url": "https://www.census.gov/data/developers/data-sets/international-trade.html",
            "first_month": str(df["month"].min()),
            "last_month": str(df["month"].max()),
            "synthetic": (args.raw_dir / "_SYNTHETIC").exists(),
            "checks": checks,
            "hs_codes": HS_CODES,
            "products": PRODUCTS,
        },
        "events": events.to_dict(orient="records"),
        "views": views,
    }
    out = args.out_dir / "dashboard_data.json"
    out.write_text(json.dumps(data, separators=(",", ":")))
    print(f"\nWrote {out} ({out.stat().st_size / 1024:.0f} KB). Next: python src/build_dashboard.py")


if __name__ == "__main__":
    main()
