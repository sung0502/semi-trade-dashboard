-- Views over the processed CSVs. sql/query.py replaces {data_dir} and {events_csv} before running.
-- quote='"' is required: some country names contain commas (e.g. "Svalbard, Jan Mayen Island").

-- One row per flow, HS code, month and country. value is in current U.S. dollars.
CREATE OR REPLACE VIEW trade AS
SELECT flow, hs, month, cty_code, country, value,
       CAST(LEFT(month, 4) AS INTEGER) AS year,
       CAST(month || '-01' AS DATE) AS month_start
FROM read_csv('{data_dir}/trade_monthly.csv',
              types = {'hs': 'VARCHAR', 'month': 'VARCHAR', 'cty_code': 'VARCHAR'}, quote = '"');

-- Calendar-year values and shares by country; product includes the derived 'chips' (8541 + 8542).
CREATE OR REPLACE VIEW annual AS
SELECT * FROM read_csv('{data_dir}/trade_annual.csv', types = {'product': 'VARCHAR'}, quote = '"');

-- Calendar-year total, top supplier, top-3 share and HHI per flow and product.
CREATE OR REPLACE VIEW concentration AS
SELECT * FROM read_csv('{data_dir}/concentration_annual.csv', types = {'product': 'VARCHAR'}, quote = '"');

-- Policy events with dates and sources.
CREATE OR REPLACE VIEW events AS
SELECT CAST(date AS DATE) AS event_date, short_name, type, description, affects, source_url, notes
FROM read_csv('{events_csv}', all_varchar = true, quote = '"');
