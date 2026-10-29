# HS classification breaks

The Harmonized System is revised about every five years. The U.S. Harmonized Tariff Schedule (HTS) adopted the 2017 and 2022 editions on January 1 of each year, and the dashboard marks both dates with a dashed line. When a product moves into or out of a heading, the HS4 series jumps for reasons that have nothing to do with trade.

**Status: the items below are from memory of the WCO amendments and must be checked against the WCO correlation tables (HS 2012 to 2017, HS 2017 to 2022) and the HTS archive at https://hts.usitc.gov/ before publishing.** Tick each one off in `NOTES.md` once confirmed.

| Edition | Heading | Change (to verify) | Likely effect on this series |
|---|---|---|---|
| HS 2017 | 8542 | Chapter 85 note on electronic integrated circuits widened to cover multi-component ICs (MCOs) | Some products previously classified elsewhere move into 8542; small upward shift possible |
| HS 2022 | 8541 | Photosensitive devices split out (LEDs, photovoltaic cells not in modules, photovoltaic cells in modules) | Mostly a split within 8541; the HS4 total should be largely continuous |
| HS 2022 | 8541 | New subheadings for semiconductor-based transducers (sensors) | Sensors previously classified in other headings move into 8541; upward shift possible |
| HS 2022 | 8486 | Check whether any subheadings changed | Unknown |

## Other things that move these series

- **Solar cells are in 8541.** Photovoltaic cells and modules are a large share of 8541 imports, so the 8541 series reflects the solar market and solar trade actions (Section 201 safeguard from 2018, antidumping and countervailing duties on Southeast Asian cells) as much as chips. Consider showing 8542 alone as the headline "chips" view, or splitting out the solar subheadings at HS6 in a later version.
- **Census revisions.** Recent months are revised; the fetch script re-downloads the last two years on every run.
- **Country of origin** is where the last substantial transformation happened, often assembly and test, not wafer fabrication.

## How to check a break

1. In the dashboard, look at the monthly series for the heading around January of the revision year.
2. In USA Trade Online, pull the HS6 lines for the same heading for the 12 months on each side of the break.
3. If a new HS6 line appears with substantial value in January, record its size in `NOTES.md` and mention it in the event-window caveats.
