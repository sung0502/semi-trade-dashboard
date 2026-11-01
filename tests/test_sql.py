"""SQL layer tests: every query file runs, and SQL HHI matches the Python pipeline.
Run with:  python -m pytest tests"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sql"))
sys.path.insert(0, str(ROOT / "tests"))
from query import SQL_DIR, connect, split_queries  # noqa: E402
import make_fixture  # noqa: E402


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw")
    out = tmp_path_factory.mktemp("out")
    make_fixture.main(raw)
    subprocess.run([sys.executable, str(ROOT / "src" / "process.py"), "--raw-dir", str(raw), "--out-dir", str(out)],
                   check=True, capture_output=True)
    return connect(out)


def test_split_ignores_semicolons_inside_lines():
    text = "-- name: A\nSELECT 1; -- not a split\n;\n-- only a comment;\nSELECT 'x;y';\n"
    queries = list(split_queries(text))
    assert [t for t, _ in queries] == ["A", None]
    assert "'x;y'" in queries[1][1]


def test_every_query_file_runs(con):
    for path in sorted(SQL_DIR.glob("[0-9]*.sql")):
        for _, sql in split_queries(path.read_text()):
            con.sql(sql).fetchall()


def test_sql_hhi_matches_python(con):
    sql = (SQL_DIR / "02_hhi_check.sql").read_text()
    rows = con.sql(list(split_queries(sql))[0][1]).fetchall()
    assert len(rows) == 6
    assert max(r[-1] for r in rows) < 0.05
