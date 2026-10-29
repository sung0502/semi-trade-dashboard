"""Embed processed data into the HTML template to produce a single self-contained file.

Usage:
    python src/build_dashboard.py
Output: dashboard.html (open it in any browser, or publish it with GitHub Pages).
"""
import argparse
from pathlib import Path

from config import OUTPUT_HTML, PROCESSED_DIR, TEMPLATE

PLACEHOLDER = "/*__DATA__*/null"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=PROCESSED_DIR / "dashboard_data.json")
    parser.add_argument("--out", type=Path, default=OUTPUT_HTML)
    args = parser.parse_args()

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit("Template is missing the data placeholder.")
    data = args.data.read_text(encoding="utf-8")
    # Stop a stray "</script>" inside the data from closing the script tag early.
    data = data.replace("</", "<\\/")
    html = template.replace(PLACEHOLDER, data)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
