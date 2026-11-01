"""Streamlit dashboard: U.S. semiconductor trade dependence.

Run locally:
    streamlit run app.py

Reads data/processed/ (built by src/process.py) and data/events.csv. To preview with the
synthetic fixture instead, set SEMI_DATA_DIR=tests/fixture_out.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from config import EVENT_WINDOW_MONTHS, EVENTS_CSV, HS_BREAKS, PROCESSED_DIR, PRODUCTS, TOP_N  # noqa: E402
from metrics import (annual_concentration, hhi, hhi_label, rolling_12, shares,  # noqa: E402
                     top_k_share, window_comparison)
from process import monthly_wide  # noqa: E402

DATA_DIR = ROOT / os.environ["SEMI_DATA_DIR"] if os.environ.get("SEMI_DATA_DIR") else PROCESSED_DIR

# Same categorical order as the static HTML dashboard; colour follows the country, not its rank.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
OTHER_COLOR = "#c3c2b7"
NEG_COLOR = "#e34948"
FLOW_WORD = {"imports": "supplier", "exports": "destination"}

st.set_page_config(page_title="U.S. Semiconductor Trade Dependence", layout="wide")


@st.cache_data
def load(data_dir: str, _version: tuple):
    """Load the data. `_version` holds file modification times, so the cache refreshes when
    a redeploy changes the data or the events table instead of serving the old copy."""
    data_dir = Path(data_dir)
    df = pd.read_csv(data_dir / "trade_monthly.csv", dtype={"hs": str, "cty_code": str})
    events = pd.read_csv(EVENTS_CSV, dtype=str).fillna("").sort_values("date").reset_index(drop=True)
    meta = json.loads((data_dir / "dashboard_data.json").read_text())["meta"]
    return df, events, meta


def money(v):
    a = abs(v)
    if a >= 1e12:
        return f"${v / 1e12:.2f}T"
    if a >= 1e9:
        return f"${v / 1e9:.1f}B"
    return f"${v / 1e6:.0f}M"


def base_layout(fig, height, yaxis):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, traceorder="normal"), yaxis=yaxis,
                      plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


def mark_dates(fig, events, start, end):
    """Dotted lines for policy events, dashed grey lines for HS classification breaks.

    Events are labelled with their number from event_key() rather than their name, since
    events a few months apart would otherwise print on top of each other. Neighbouring
    numbers alternate between two heights for the same reason.
    """
    for i, ev in events.iterrows():
        m = pd.Period(ev["date"], freq="M")
        if start <= m <= end:
            fig.add_vline(x=m.to_timestamp(), line=dict(color="rgba(128,128,128,0.7)", width=1, dash="dot"))
            fig.add_annotation(x=m.to_timestamp(), y=1 if i % 2 == 0 else 0.92, yref="paper", text=f"<b>{i + 1}</b>",
                               hovertext=f"{ev['short_name']} ({ev['date']})", showarrow=False,
                               yanchor="top", font=dict(size=11, color="#0b0b0b"),
                               bgcolor="rgba(255,255,255,0.85)", borderpad=2)
    for month, label in HS_BREAKS.items():
        m = pd.Period(month, freq="M")
        if start <= m <= end:
            fig.add_vline(x=m.to_timestamp(), line=dict(color="rgba(128,128,128,0.5)", width=1, dash="dash"))
            fig.add_annotation(x=m.to_timestamp(), y=0, yref="paper", text=label, showarrow=False,
                               xanchor="left", yanchor="bottom", font=dict(size=10, color="gray"))


def event_key(events, start, end):
    """Caption text mapping each event number on the charts to its name and date."""
    items = [f"**{i + 1}** {ev['short_name']} ({pd.Period(ev['date'], freq='M').strftime('%b %Y')})"
             for i, ev in events.iterrows() if start <= pd.Period(ev["date"], freq="M") <= end]
    return "Events: " + " · ".join(items) if items else ""


if not (DATA_DIR / "trade_monthly.csv").exists():
    st.error(f"No processed data in {DATA_DIR}. Run src/fetch_census.py and src/process.py first.")
    st.stop()

version = tuple(p.stat().st_mtime for p in (DATA_DIR / "trade_monthly.csv", DATA_DIR / "dashboard_data.json", EVENTS_CSV))
df, events, meta = load(str(DATA_DIR), version)

st.title("U.S. Semiconductor Trade Dependence")
st.caption(
    "Who the U.S. buys chips and chipmaking equipment from, how concentrated that supplier base is, "
    f"and how it shifted around tariff and export-control actions. Source: [{meta['source']}]({meta['source_url']}), "
    f"{meta['first_month']} to {meta['last_month']}. Values in current U.S. dollars."
)
if meta.get("synthetic"):
    st.warning("Synthetic test data: these numbers are made up and are not real trade figures.")

# ---------- filters ----------
c1, c2, c3 = st.columns([1, 2, 3])
flow = c1.radio("Flow", ["imports", "exports"], horizontal=True, format_func=str.capitalize)
product = c2.selectbox("Product (HS code)", list(PRODUCTS), format_func=PRODUCTS.get)
wide = monthly_wide(df, flow, product)
if len(wide) < 12:
    st.info("Fewer than 12 months of data for this selection.")
    st.stop()

r12_full = rolling_12(wide).dropna(how="all")
months = [p.to_timestamp().date() for p in r12_full.index]
start_d, end_d = c3.select_slider("Time range (trailing 12-month windows ending in)", options=months,
                                  value=(months[0], months[-1]), format_func=lambda d: d.strftime("%b %Y"))
start, end = pd.Period(start_d, freq="M"), pd.Period(end_d, freq="M")

# Rolling sums are computed on the full series and then sliced, so the first month in the
# range still has a full 12-month window behind it.
r12 = r12_full.loc[start:end]
sh = shares(r12)
h = hhi(sh)
t3 = top_k_share(sh, 3)
word = FLOW_WORD[flow]

# ---------- headline numbers ----------
latest, prior = r12.index[-1], r12.index[-1] - 12
has_prior = prior in r12_full.index
latest_share = sh.loc[latest]
top_country = latest_share.idxmax()
k1, k2, k3, k4 = st.columns(4)
total = r12.loc[latest].sum()
k1.metric(f"12-month {flow}, to {latest.strftime('%b %Y')}", money(total),
          f"{(total / r12_full.loc[prior].sum() - 1) * 100:+.1f}% vs year earlier" if has_prior else None)
k2.metric(f"Largest {word}", top_country, f"{latest_share[top_country] * 100:.1f}% share", delta_color="off")
k3.metric(f"Top-3 {word} share", f"{t3.loc[latest] * 100:.1f}%")
prior_h = hhi(shares(r12_full.loc[[prior]])).iloc[0] if has_prior else None
k4.metric("HHI (0 to 10,000)", f"{h.loc[latest]:,.0f}",
          f"{h.loc[latest] - prior_h:+,.0f} vs year earlier" if has_prior else None, delta_color="inverse",
          help=f"{hhi_label(h.loc[latest])}. 2023 DOJ/FTC guidelines: above 1,800 is highly concentrated, "
               "1,000 to 1,800 moderately concentrated.")

# ---------- supplier shares ----------
st.subheader(f"{word.capitalize()} shares over time")
st.caption("Share of trailing 12-month value. Numbered dotted lines mark policy events (hover for the name); "
           "dashed lines mark HS revisions.")
top = r12.sum().sort_values(ascending=False).head(TOP_N).index.tolist()
x = [p.to_timestamp() for p in sh.index]
fig = go.Figure()
for i, c in enumerate(top + ["Other"]):
    y = sh.drop(columns=top).sum(axis=1) if c == "Other" else sh[c]
    color = OTHER_COLOR if c == "Other" else SERIES_COLORS[i]
    fig.add_trace(go.Scatter(x=x, y=y * 100, name=c, stackgroup="one", mode="lines",
                             line=dict(width=0.5, color=color), fillcolor=color,
                             hovertemplate="%{y:.1f}%"))
mark_dates(fig, events, start, end)
st.plotly_chart(base_layout(fig, 420, dict(title="Share (%)", range=[0, 100], ticksuffix="%")),
                use_container_width=True)
st.caption(event_key(events, start, end))

# ---------- concentration ----------
st.subheader("Concentration (HHI)")
st.caption("Herfindahl-Hirschman Index on trailing 12-month shares. Rising means a more concentrated supplier base.")
fig = go.Figure()
ymax = max(2500, float(h.max()) * 1.1)
fig.add_hrect(y0=1000, y1=1800, fillcolor="rgba(128,128,128,0.08)", line_width=0,
              annotation_text="Moderately concentrated", annotation_position="top left")
fig.add_hrect(y0=1800, y1=ymax, fillcolor="rgba(128,128,128,0.16)", line_width=0,
              annotation_text="Highly concentrated", annotation_position="top left")
fig.add_trace(go.Scatter(x=x, y=h, name="HHI", mode="lines", line=dict(width=2, color=SERIES_COLORS[0]),
                         hovertemplate="%{y:,.0f}"))
mark_dates(fig, events, start, end)
st.plotly_chart(base_layout(fig, 320, dict(title="HHI", range=[0, ymax])).update_layout(showlegend=False),
                use_container_width=True)
st.caption(event_key(events, start, end))

# ---------- event windows ----------
st.subheader("Around a policy event")
labels = {f"{i + 1}. {ev['short_name']} ({ev['date']})": i for i, ev in events.iterrows()}
choice = st.selectbox("Event", list(labels))
ev = events.loc[labels[choice]]
ev_month = pd.Period(ev["date"], freq="M")
st.markdown(f"{ev['description']}. [Primary source]({ev['source_url']})"
            + (f"  \n*Note: {ev['notes']}*" if ev["notes"] else ""))
res = window_comparison(wide, ev_month, EVENT_WINDOW_MONTHS)
if res is None:
    st.info(f"Not enough data yet for a full {EVENT_WINDOW_MONTHS}-month window on both sides of this event.")
else:
    before, after = res
    b_sh, a_sh = before / before.sum(), after / after.sum()
    comp = pd.DataFrame({"before": b_sh * 100, "after": a_sh * 100})
    comp["change_pp"] = comp["after"] - comp["before"]
    comp = comp.loc[comp["change_pp"].abs().sort_values(ascending=False).head(10).index].sort_values("change_pp")
    window = f"{(ev_month - EVENT_WINDOW_MONTHS).strftime('%b %Y')} to {(ev_month - 1).strftime('%b %Y')} vs " \
             f"{(ev_month + 1).strftime('%b %Y')} to {(ev_month + EVENT_WINDOW_MONTHS).strftime('%b %Y')}"
    st.caption(f"Change in share, percentage points: {window} (event month excluded). "
               f"Total value changed {(after.sum() / before.sum() - 1) * 100:+.1f}%. "
               "This shows association, not causation.")
    breaks = [lbl for m, lbl in HS_BREAKS.items()
              if ev_month - EVENT_WINDOW_MONTHS <= pd.Period(m, freq="M") <= ev_month + EVENT_WINDOW_MONTHS]
    if breaks:
        st.warning(f"The {' and '.join(breaks)} falls inside this window, so part of the change may be "
                   "reclassification. See docs/HS_REVISIONS.md.")
    fig = go.Figure(go.Bar(
        x=comp["change_pp"], y=comp.index, orientation="h",
        marker=dict(color=[SERIES_COLORS[0] if v >= 0 else NEG_COLOR for v in comp["change_pp"]],
                    cornerradius=4),
        customdata=comp[["before", "after"]].values,
        hovertemplate="%{y}: %{customdata[0]:.1f}% → %{customdata[1]:.1f}% (%{x:+.2f} pp)<extra></extra>"))
    fig.update_layout(height=40 * len(comp) + 60, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="Change in share (pp)", zeroline=True, zerolinecolor="gray",
                                 gridcolor="rgba(128,128,128,0.2)"),
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Before and after shares as a table"):
        st.dataframe(comp.iloc[::-1].round(2), use_container_width=True)

# ---------- annual table ----------
st.subheader("By calendar year")
yearly = annual_concentration(wide)
yearly = yearly[(yearly.index >= start.year) & (yearly.index <= end.year)]
table = pd.DataFrame({
    "Year": [f"{y} (YTD, {m} mo)" if m < 12 else str(y) for y, m in zip(yearly.index, yearly["months"])],
    "Total": yearly["total"].map(money),
    f"Top {word}": yearly["top_country"],
    "Top share": (yearly["top_share"] * 100).map("{:.1f}%".format),
    "Top-3 share": (yearly["top3_share"] * 100).map("{:.1f}%".format),
    "HHI": yearly["hhi"].map("{:,.0f}".format),
})
st.dataframe(table, hide_index=True, use_container_width=True)
st.download_button("Download monthly data (CSV)", wide.to_csv().encode(), f"{flow}_{product}_monthly.csv",
                   "text/csv")

# ---------- method ----------
with st.expander("Method and limitations"):
    checks = meta.get("checks", {})
    st.markdown(f"""
- **Countries.** Individual countries only; Census groupings (EU, APEC, regions) are dropped so nothing is
  double counted. Country rows reconcile to the Census all-countries total: {checks.get('status', 'n/a')}
  (largest monthly gap {checks.get('max_pct_difference', 'n/a')}%).
- **Shares and HHI** use trailing 12-month sums. HHI is the sum of squared percentage shares.
- **Country of origin** for chips is often where the chip was assembled and tested, not where the wafer
  was made, which is why Malaysia or Vietnam can outrank Taiwan.
- **HS revisions** in 2017 and 2022 changed what falls under 8541 and 8542, so compare across those dates
  with care. HS 8541 also includes solar cells, which can dominate its totals.
- **Event windows** compare the {EVENT_WINDOW_MONTHS} full months before and after each event. Demand cycles
  and the 2021 shortage move trade at the same time, so these are associations, not effects.

Code, sources and verification notes: see the project README.
""")
