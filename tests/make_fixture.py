"""Generate SYNTHETIC raw files in the Census API format, for testing the pipeline offline.

The numbers are made up. The output folder gets a _SYNTHETIC marker file, and the
dashboard shows a warning banner whenever it is built from this data.

Usage:
    python tests/make_fixture.py tests/fixture_raw
"""
import json
import math
import random
import sys
from pathlib import Path

COUNTRIES = {
    "5570": "MALAYSIA", "5830": "TAIWAN", "5520": "VIETNAM", "5700": "CHINA",
    "5800": "KOREA, SOUTH", "5880": "JAPAN", "2010": "MEXICO", "5490": "THAILAND",
    "5650": "PHILIPPINES", "4190": "IRELAND", "5081": "ISRAEL", "4210": "NETHERLANDS",
    "4280": "GERMANY", "5590": "SINGAPORE", "1220": "CANADA",
}
FIELDS = {"imports": ("GEN_VAL_MO", "I_COMMODITY"), "exports": ("ALL_VAL_MO", "E_COMMODITY")}


def main(out_dir: Path):
    rnd = random.Random(42)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_SYNTHETIC").write_text("synthetic test data - not real trade figures\n")
    base = {c: rnd.uniform(0.2, 3.0) for c in COUNTRIES}
    for flow, (value_field, comm_field) in FIELDS.items():
        for hs, scale in {"8541": 4e8, "8542": 2e9, "8486": 6e8}.items():
            for year in range(2015, 2027):
                header = ["CTY_CODE", "CTY_NAME", value_field, "COMM_LVL", comm_field, "time"]
                rows = [header]
                for m in range(1, 13):
                    if year == 2026 and m > 8:
                        break
                    t = (year - 2015) + m / 12
                    month_total = 0
                    for code, name in COUNTRIES.items():
                        w = base[code] * (1 + 0.04 * t)
                        if code == "5700":  # China declines after 2018
                            w *= 1.6 if t < 3.5 else max(0.3, 1.6 - 0.25 * (t - 3.5))
                        if code in ("5520", "2010"):  # Vietnam, Mexico rise
                            w *= 1 + max(0, t - 3.5) * 0.18
                        v = round(scale * w / 10 * (1 + 0.08 * math.sin(m)) * rnd.uniform(0.9, 1.1))
                        month_total += v
                        rows.append([code, name, str(v), "HS4", hs, f"{year}-{m:02d}"])
                    rows.append(["0003", "EUROPEAN UNION", "123", "HS4", hs, f"{year}-{m:02d}"])
                    rows.append(["5XXX", "ASIA", "456", "HS4", hs, f"{year}-{m:02d}"])
                    rows.append(["-", "TOTAL FOR ALL COUNTRIES", str(month_total), "HS4", hs, f"{year}-{m:02d}"])
                payload = {"flow": flow, "hs": hs, "year": year, "retrieved_utc": "synthetic", "rows": rows}
                (out_dir / f"{flow}_{hs}_{year}.json").write_text(json.dumps(payload))
    print(f"Wrote synthetic fixture to {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixture_raw"))
