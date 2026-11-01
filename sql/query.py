"""Run SQL analyses on the processed trade data with DuckDB.

Usage:
    python sql/query.py sql/03_chips_act_equipment.sql     # run every query in a file
    python sql/query.py --all                              # run every numbered .sql file
    python sql/query.py --save data/trade.duckdb           # write a database file for DBeaver, the
                                                           # duckdb CLI, or a notebook

The views it creates (trade, annual, concentration, events) are defined in sql/schema.sql.
Queries in a file are separated by a semicolon at the end of a line. A "-- name:" comment above
a query is printed as its title.
"""
import argparse
import os
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import EVENTS_CSV, PROCESSED_DIR  # noqa: E402

SQL_DIR = ROOT / "sql"


def connect(data_dir: Path = PROCESSED_DIR, database: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Open DuckDB with the trade, annual, concentration and events views defined."""
    con = duckdb.connect(database)
    schema = (SQL_DIR / "schema.sql").read_text()
    schema = schema.replace("{data_dir}", data_dir.as_posix()).replace("{events_csv}", EVENTS_CSV.as_posix())
    con.execute(schema)
    return con


def split_queries(text: str):
    """Yield (title, sql) for each statement, using a '-- name:' comment as the title."""
    # Split only on a semicolon that ends a line, so one inside a comment or string is kept.
    for chunk in re.split(r";[ \t]*(?:\n|$)", text):
        sql = chunk.strip()
        if not re.sub(r"--[^\n]*", "", sql).strip():
            continue
        m = re.search(r"--\s*name:\s*(.+)", sql)
        yield (m.group(1).strip() if m else None), sql


def run_file(con, path: Path):
    print(f"\n#### {path.name}")
    for title, sql in split_queries(path.read_text()):
        if title:
            print(f"\n== {title}")
        result = con.sql(sql)
        if result is not None:
            result.show(max_width=160, max_rows=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--all", action="store_true", help="run every numbered .sql file in sql/")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("SEMI_DATA_DIR", PROCESSED_DIR)))
    parser.add_argument("--save", metavar="PATH", help="also write a DuckDB database file with the views")
    args = parser.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # DuckDB draws tables with box characters

    con = connect(args.data_dir.resolve(), args.save or ":memory:")
    if args.save:
        print(f"Saved views to {args.save}. Open it with: duckdb {args.save}")
    files = sorted(SQL_DIR.glob("[0-9]*.sql")) if args.all else args.files
    if not files and not args.save:
        parser.error("give one or more .sql files, --all, or --save")
    for path in files:
        run_file(con, path)


if __name__ == "__main__":
    main()
