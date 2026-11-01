-- Verification: recompute the annual HHI from the monthly data in SQL and compare it with
-- the Python pipeline's concentration_annual.csv. The two are written independently, so
-- matching results are a check on both. Expect max_abs_diff close to 0.

-- name: Largest gap between SQL and Python HHI, by flow and HS code
WITH yearly AS (
    SELECT flow, hs, year, country, SUM(value) AS value
    FROM trade
    GROUP BY ALL
),
shares AS (
    SELECT *, 100 * value / SUM(value) OVER (PARTITION BY flow, hs, year) AS share
    FROM yearly
),
sql_hhi AS (
    SELECT flow, hs, year, SUM(share * share) AS hhi
    FROM shares
    GROUP BY ALL
)
SELECT s.flow, s.hs,
       COUNT(*) AS years,
       ROUND(MAX(ABS(s.hhi - c.hhi)), 4) AS max_abs_diff
FROM sql_hhi s
JOIN concentration c ON c.flow = s.flow AND c.product = s.hs AND c.year = s.year
GROUP BY ALL
ORDER BY s.flow, s.hs;
