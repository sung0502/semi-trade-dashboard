"""Shared settings for the semiconductor trade dashboard pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
EVENTS_CSV = ROOT / "data" / "events.csv"
TEMPLATE = ROOT / "templates" / "dashboard_template.html"
OUTPUT_HTML = ROOT / "dashboard.html"

START_YEAR = 2015

# HS4 codes tracked. "chips" is a derived product = 8541 + 8542.
HS_CODES = {
    "8541": "Discrete semiconductors (diodes, transistors, LEDs, solar cells)",
    "8542": "Integrated circuits (processors, memory, logic)",
    "8486": "Semiconductor manufacturing equipment",
}
PRODUCTS = {
    "chips": "All chips (8541 + 8542)",
    "8542": "Integrated circuits (8542)",
    "8541": "Discrete semiconductors (8541)",
    "8486": "Manufacturing equipment (8486)",
}
DERIVED = {"chips": ["8541", "8542"]}

# Census International Trade API endpoints and the value field used for each flow.
# Imports: general imports value by country of origin.
# Exports: total exports value (domestic + foreign) by country of destination.
FLOWS = {
    "imports": {
        "url": "https://api.census.gov/data/timeseries/intltrade/imports/hs",
        "commodity_field": "I_COMMODITY",
        "value_field": "GEN_VAL_MO",
    },
    "exports": {
        "url": "https://api.census.gov/data/timeseries/intltrade/exports/hs",
        "commodity_field": "E_COMMODITY",
        "value_field": "ALL_VAL_MO",
    },
}

# HS nomenclature revisions that can break the series (see docs/HS_REVISIONS.md).
# The U.S. HTS adopted each edition on January 1 of that year.
HS_BREAKS = {
    "2017-01": "HS 2017 revision",
    "2022-01": "HS 2022 revision",
}

# Number of named countries in the share chart; the rest fold into "Other".
TOP_N = 5
# Months on each side of a policy event used for before/after comparison.
EVENT_WINDOW_MONTHS = 12
