"""Download monthly U.S. semiconductor trade by country from the Census International Trade API.

Usage:
    python src/fetch_census.py                 # 2015 through the current year
    python src/fetch_census.py --start 2018    # custom start year
    python src/fetch_census.py --refresh       # re-download every file

An API key is required (free: https://api.census.gov/data/key_signup.html).
Set it with:  export CENSUS_API_KEY=your_key

Each request is saved untouched to data/raw/<flow>_<hs>_<year>.json so the pipeline can be
re-run offline and every number can be traced back to the original response. Every pull is
also appended to data/raw/pull_log.csv with its UTC date, row count and SHA-256, so you can
tell exactly which download a processed figure came from.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import sys
import time

import requests

from config import FLOWS, HS_CODES, RAW_DIR, START_YEAR

TIMEOUT = 60
RETRIES = 3


def build_params(flow_cfg, hs, time_value, api_key):
    params = {
        "get": f"CTY_CODE,CTY_NAME,{flow_cfg['value_field']}",
        "COMM_LVL": "HS4",
        flow_cfg["commodity_field"]: hs,
        "time": time_value,
    }
    if api_key:
        params["key"] = api_key
    return params


def request_rows(url, params):
    """Return the API's list-of-lists response, [] when Census has no data (HTTP 204)."""
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT, allow_redirects=False)
        except requests.RequestException as exc:
            if attempt == RETRIES:
                raise
            print(f"    network error ({exc}); retrying...")
            time.sleep(2 * attempt)
            continue
        if resp.status_code in (301, 302) and "missing_key" in resp.headers.get("Location", ""):
            raise SystemExit("Census rejected the request: a valid CENSUS_API_KEY is required.")
        if resp.status_code == 204:
            return []
        if resp.status_code == 200:
            return resp.json()
        if attempt == RETRIES or resp.status_code in (400, 404):
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        time.sleep(2 * attempt)
    return []


def fetch_year(flow, hs, year, api_key):
    """Fetch one calendar year. Tries a single range query, falls back to month by month."""
    cfg = FLOWS[flow]
    last_month = 12
    today = dt.date.today()
    if year == today.year:
        last_month = today.month
    try:
        rows = request_rows(cfg["url"], build_params(cfg, hs, f"from {year}-01 to {year}-{last_month:02d}", api_key))
        return rows
    except RuntimeError as exc:
        print(f"    range query failed ({exc}); falling back to monthly requests")

    header, body = None, []
    for m in range(1, last_month + 1):
        rows = request_rows(cfg["url"], build_params(cfg, hs, f"{year}-{m:02d}", api_key))
        if rows:
            header = header or rows[0]
            body.extend(rows[1:])
    return [header] + body if header else []


def log_pull(path, payload, text):
    log = RAW_DIR / "pull_log.csv"
    new = not log.exists()
    with log.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["retrieved_utc", "file", "flow", "hs", "year", "rows", "sha256"])
        w.writerow([payload["retrieved_utc"], path.name, payload["flow"], payload["hs"], payload["year"],
                    max(len(payload["rows"]) - 1, 0), hashlib.sha256(text.encode()).hexdigest()])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=int, default=START_YEAR)
    parser.add_argument("--end", type=int, default=dt.date.today().year)
    parser.add_argument("--refresh", action="store_true", help="re-download files that already exist")
    args = parser.parse_args()

    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        raise SystemExit("Set CENSUS_API_KEY first (free key: https://api.census.gov/data/key_signup.html).")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    this_year = dt.date.today().year
    failures = []

    for flow in FLOWS:
        for hs in HS_CODES:
            for year in range(args.start, args.end + 1):
                path = RAW_DIR / f"{flow}_{hs}_{year}.json"
                # Recent years get revised, so always refresh the last two.
                recent = year >= this_year - 1
                if path.exists() and not args.refresh and not recent:
                    continue
                print(f"Fetching {flow} HS {hs} {year} ...")
                try:
                    rows = fetch_year(flow, hs, year, api_key)
                except Exception as exc:  # keep going; report at the end
                    print(f"    FAILED: {exc}")
                    failures.append((flow, hs, year, str(exc)))
                    continue
                payload = {
                    "flow": flow,
                    "hs": hs,
                    "year": year,
                    "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "rows": rows,
                }
                text = json.dumps(payload)
                path.write_text(text)
                log_pull(path, payload, text)
                print(f"    saved {max(len(rows) - 1, 0)} rows")
                time.sleep(0.3)

    if failures:
        print(f"\n{len(failures)} request(s) failed:")
        for f in failures:
            print("  ", f)
        sys.exit(1)
    print("\nDone. Next: python src/process.py")


if __name__ == "__main__":
    main()
