# Verification notes

A running log of what has been checked against the source and what could not be verified. Update it every time the data is refreshed.

## Data pull

- [ ] Latest pull date and row counts recorded (see `data/raw/pull_log.csv`)
- [ ] `data/processed/checks.json` status is `ok` (country rows reconcile to the Census all-countries total)

## Annual totals vs Census published figures

Run `python src/verify.py`, then compare with USA Trade Online (https://usatrade.census.gov/).

| Flow | HS | Year | Our total ($M) | Census published ($M) | Difference | Checked on |
|---|---|---|---|---|---|---|
| imports | 8542 | 2024 | | | | |
| imports | 8541 | 2024 | | | | |
| imports | 8486 | 2024 | | | | |

## Country spot checks

Run `python src/verify.py --spot COUNTRY MONTH FLOW HS` and compare with the source table.

| Country | Month | Flow | HS | Ours | Source | Match? |
|---|---|---|---|---|---|---|
| Taiwan | | imports | 8542 | | | |
| Malaysia | | imports | 8542 | | | |
| Netherlands | | imports | 8486 | | | |

## Event windows

For each event, recompute the before and after shares independently (notebook or spreadsheet from `trade_monthly.csv`) and confirm they match the dashboard.

| Event | Product | Dashboard top mover (pp) | Recomputed | Match? |
|---|---|---|---|---|

## Event dates and sources

- [ ] 2018-07-06 Section 301 List 1: confirm which semiconductor HTS lines List 1 covered (USTR annex)
- [ ] 2018-08-23 Section 301 List 2: source is a law-firm alert, not primary. Replace with the Federal Register notice and confirm semiconductor coverage
- [ ] 2022-10-07 BIS controls: confirm the effective date against the Federal Register rule (published 2022-10-13)
- [ ] 2023-10-17 BIS update: confirm against the Federal Register rules (published 2023-10-19)
- [ ] 2025-01-01 Section 301 increase: confirm against the USTR final determination
- [ ] 2025-04-01 Section 232 investigation: source is a law-firm page, not primary. Replace with the Federal Register notice (published 2025-04-16)

## HS revisions

- [ ] Each row in `docs/HS_REVISIONS.md` confirmed against the WCO correlation tables

## Could not verify

(List anything here that you checked and could not confirm, with the reason.)
