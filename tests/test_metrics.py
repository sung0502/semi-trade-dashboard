"""Unit tests for the metric functions. Run with:  python -m pytest tests"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from metrics import (annual_concentration, hhi, hhi_label, rolling_12, shares, top_k_share,  # noqa: E402
                     window_comparison)
from process import is_country  # noqa: E402


def test_hhi_monopoly_and_even_split():
    one = pd.DataFrame({"A": [1.0]})
    assert hhi(shares(one)).iloc[0] == 10000
    four = pd.DataFrame({"A": [1.0], "B": [1.0], "C": [1.0], "D": [1.0]})
    assert round(hhi(shares(four)).iloc[0]) == 2500  # 4 x 25^2


def test_hhi_known_example():
    df = pd.DataFrame({"A": [50.0], "B": [30.0], "C": [20.0]})
    assert round(hhi(shares(df)).iloc[0]) == 50**2 + 30**2 + 20**2  # 3800


def test_labels_follow_2023_guidelines():
    assert hhi_label(900) == "Unconcentrated"
    assert hhi_label(1500) == "Moderately concentrated"
    assert hhi_label(1801) == "Highly concentrated"


def test_top3_share():
    df = pd.DataFrame({"A": [40.0], "B": [30.0], "C": [20.0], "D": [10.0]})
    assert abs(top_k_share(shares(df), 3).iloc[0] - 0.9) < 1e-9


def test_rolling_needs_full_year():
    idx = pd.period_range("2020-01", periods=13, freq="M")
    df = pd.DataFrame({"A": [1.0] * 13}, index=idx)
    out = rolling_12(df)
    assert out["A"].isna().sum() == 11
    assert out["A"].iloc[-1] == 12


def test_event_window_excludes_event_month():
    idx = pd.period_range("2020-01", "2022-12", freq="M")
    df = pd.DataFrame({"A": range(len(idx))}, index=idx, dtype=float)
    before, after = window_comparison(df, pd.Period("2021-06", freq="M"), 12)
    assert before["A"] == sum(range(5, 17))   # 2020-06 .. 2021-05
    assert after["A"] == sum(range(18, 30))   # 2021-07 .. 2022-06
    assert window_comparison(df, pd.Period("2022-06", freq="M"), 12) is None


def test_country_filter_drops_groupings_and_totals():
    assert is_country("5700")
    assert not is_country("0003")   # European Union grouping
    assert not is_country("5XXX")   # Asia region total
    assert not is_country("-")      # all countries total


def test_annual_concentration_flags_partial_year():
    idx = pd.period_range("2020-01", "2021-03", freq="M")
    df = pd.DataFrame({"A": [3.0] * len(idx), "B": [1.0] * len(idx)}, index=idx)
    out = annual_concentration(df)
    assert list(out["months"]) == [12, 3]
    assert out.loc[2020, "total"] == 48
    assert out.loc[2020, "top_country"] == "A"
    assert round(out.loc[2020, "hhi"]) == 75**2 + 25**2
