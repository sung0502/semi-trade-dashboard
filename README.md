# U.S. Semiconductor Trade Dependence Dashboard

An interactive dashboard showing where the United States buys and sends semiconductors and chipmaking equipment, how concentrated those trading partners are, and how trade shifted around major tariff and export-control actions.

**Live app:** *(add the Streamlit Community Cloud link here)* · **Findings:** [FINDINGS.md](FINDINGS.md)

It answers three questions:

1. **Who supplies the most?** Each country's share of U.S. imports, as a stacked area chart over time.
2. **How concentrated is each supplier base?** The top-3 share and the Herfindahl-Hirschman Index (HHI), by month and by calendar year.
3. **How did flows change around each policy event?** Each country's share in the 12 months before and after an event, in percentage points.

## Scope

- **Period:** monthly, January 2015 to the latest month Census has published.
- **Products:** HS 8541 (discrete semiconductors, including solar cells), HS 8542 (integrated circuits), the two combined as "all chips", and HS 8486 (semiconductor manufacturing equipment).
- **Flows:** imports by country of origin (the main view) and exports by country of destination.

## Quick start

```bash
pip install -r requirements.txt
export CENSUS_API_KEY=your_key      # required, free at https://api.census.gov/data/key_signup.html
python src/fetch_census.py          # download raw data to data/raw/ (about 70 requests)
python src/process.py               # clean, compute metrics, write data/processed/
streamlit run app.py                # open the dashboard at http://localhost:8501
```

On Windows PowerShell, set the key with `$env:CENSUS_API_KEY="your_key"`.

To refresh, re-run the fetch and process steps. The fetch script always re-downloads the two most recent years, because Census revises recent months, and keeps older files unless you pass `--refresh`.

`python src/build_dashboard.py` also writes `dashboard.html`, a single static file with the same data and no server, which you can publish with GitHub Pages.

## Project layout

```
app.py                   Streamlit dashboard (Plotly charts)
src/config.py            settings: HS codes, years, API endpoints, HS revision dates
src/fetch_census.py      downloads raw API responses, saved untouched, logged in pull_log.csv
src/process.py           cleaning, reconciliation, monthly and annual metrics -> data/processed/
src/metrics.py           share, HHI, top-3 share, annual and before/after window functions
src/verify.py            prints annual totals and spot checks to compare against Census tables
src/build_dashboard.py   optional static HTML version
data/events.csv          policy events with dates and primary sources
docs/HS_REVISIONS.md     HS 2017 and 2022 classification breaks
NOTES.md                 verification log: what was checked and what could not be verified
FINDINGS.md              one-page write-up of key findings
tests/                   unit tests and a synthetic data generator
```

## Testing without the API

```bash
python -m pytest tests
python tests/make_fixture.py tests/fixture_raw
python src/process.py --raw-dir tests/fixture_raw --out-dir tests/fixture_out
SEMI_DATA_DIR=tests/fixture_out streamlit run app.py
```

The fixture data is made up. The dashboard shows a "Synthetic test data" warning whenever it is built from it.

## Method

**Values.** Monthly values are in current U.S. dollars and are not adjusted for inflation. Imports use general imports (`GEN_VAL_MO`) and exports use total exports (`ALL_VAL_MO`). Every figure is in dollars from the same source, so no currency conversion is needed.

**Countries.** Only individual countries are kept, meaning Census codes of 1000 or higher. Groupings such as the EU and APEC, regional totals, and the all-countries total are dropped so nothing is counted twice. The country rows are reconciled against the all-countries total for every month, and the result is written to `data/processed/checks.json`.

**Shares and HHI.** The monthly views use trailing 12-month sums to smooth out noise; the annual table uses calendar years, and a partial latest year is labelled year-to-date. HHI is the sum of squared percentage shares, from 0 to 10,000. Under the 2023 DOJ/FTC Merger Guidelines, above 1,800 is highly concentrated and 1,000 to 1,800 is moderately concentrated. A rising HHI means the supplier base is becoming more concentrated.

**Event windows.** Each event is compared using the 12 full months before it and the 12 full months after it, with the event month excluded so a mid-month date doesn't split a window. The result is the change in each country's share, in percentage points.

## Known limitations

- **Association, not causation.** Demand cycles, the 2021 chip shortage, and company investment decisions move trade at the same time as policy.
- **Classification breaks.** The HS 2017 and 2022 revisions changed what falls under 8541 and 8542. The dashboard marks both dates and warns when an event window crosses one. See [docs/HS_REVISIONS.md](docs/HS_REVISIONS.md).
- **Solar cells are in 8541,** so that series reflects the solar market as well as chips.
- **Country of origin** for chips is often where the chip was assembled and tested, not where its wafer was fabricated. This is why Malaysia or Vietnam can outrank Taiwan.
- **Revisions.** Census revises recent months; figures for the latest year may change.
- **Exporter-side data** from other countries (UN Comtrade) is not yet included. It is the planned cross-check.

## Policy events

`data/events.csv` lists each event with its date, a description, and a link to its source. Each date should be checked against the original document, since summaries often get dates wrong. The `notes` column and [NOTES.md](NOTES.md) flag anything not yet confirmed. To add an event, add a row; the dashboard picks it up on the next run.

## Deploying

The app is built for Streamlit Community Cloud. `data/processed/` is committed, so the hosted app needs no API key.

1. Push this repository to GitHub (public).
2. At https://share.streamlit.io, create an app from the repository with `app.py` as the entry point.
3. Add the app link to the top of this README.

## Data source

U.S. Census Bureau, International Trade API: https://www.census.gov/data/developers/data-sets/international-trade.html
