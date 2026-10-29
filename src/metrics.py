"""Pure metric functions, kept separate so they are easy to unit test."""
import pandas as pd


def rolling_12(wide: pd.DataFrame) -> pd.DataFrame:
    """Trailing 12-month sum per column. Rows without a full 12 months become NaN."""
    return wide.rolling(12, min_periods=12).sum()


def shares(wide: pd.DataFrame) -> pd.DataFrame:
    """Each column's share (0-1) of the row total."""
    total = wide.sum(axis=1)
    return wide.div(total.where(total > 0), axis=0)


def hhi(share_df: pd.DataFrame) -> pd.Series:
    """Herfindahl-Hirschman Index on a 0-10,000 scale (shares in percent, squared, summed)."""
    return ((share_df * 100) ** 2).sum(axis=1, min_count=1)


def top_k_share(share_df: pd.DataFrame, k: int = 3) -> pd.Series:
    """Combined share of the k largest suppliers in each row."""
    return share_df.apply(lambda r: r.nlargest(k).sum() if r.notna().any() else float("nan"), axis=1)


def hhi_label(value: float) -> str:
    """Concentration band using the 2023 DOJ/FTC Merger Guidelines thresholds."""
    if value != value:  # NaN
        return "n/a"
    if value > 1800:
        return "Highly concentrated"
    if value >= 1000:
        return "Moderately concentrated"
    return "Unconcentrated"


def window_comparison(monthly: pd.DataFrame, event_month: pd.Period, months: int):
    """Compare totals in the `months` before the event month with the `months` after it.

    The event month itself is excluded so a mid-month start date does not split a window.
    Returns (before_totals, after_totals) Series indexed by country, or None if either
    window is incomplete.
    """
    before_idx = pd.period_range(event_month - months, event_month - 1, freq="M")
    after_idx = pd.period_range(event_month + 1, event_month + months, freq="M")
    if not set(before_idx).issubset(monthly.index) or not set(after_idx).issubset(monthly.index):
        return None
    return monthly.loc[before_idx].sum(), monthly.loc[after_idx].sum()


def annual_concentration(monthly: pd.DataFrame) -> pd.DataFrame:
    """Calendar-year totals, top supplier, top-3 share and HHI from a monthly wide frame.

    `months` records how many months the year contains, so a partial latest year can be
    labelled year-to-date instead of being compared with full years.
    """
    by_year = monthly.groupby(monthly.index.year)
    yearly = by_year.sum()
    sh = shares(yearly)
    return pd.DataFrame({
        "months": by_year.size(),
        "total": yearly.sum(axis=1),
        "top_country": yearly.idxmax(axis=1),
        "top_share": sh.max(axis=1),
        "top3_share": top_k_share(sh, 3),
        "hhi": hhi(sh),
    }).rename_axis("year")
