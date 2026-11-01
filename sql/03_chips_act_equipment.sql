-- Did U.S. imports of chipmaking equipment (HS 8486) rise after the CHIPS and Science Act?
--
-- The Act was signed on 2022-08-09. New fabs need tools from abroad (lithography from the
-- Netherlands, deposition and etch tools from Japan, and so on), so if the Act sped up U.S.
-- fab construction, 8486 imports should rise afterwards. Most grants were awarded in 2024, so
-- any effect may lag the signing. Chip imports (8541 + 8542) are shown alongside as a rough
-- control for the overall electronics cycle. This shows timing, not causation.

-- name: 1. Equipment imports by year, with year-over-year growth
WITH yearly AS (
    SELECT year, COUNT(DISTINCT month) AS months, SUM(value) AS value
    FROM trade
    WHERE flow = 'imports' AND hs = '8486'
    GROUP BY year
)
SELECT year,
       months,
       ROUND(value / 1e9, 2) AS usd_bn,
       -- Growth only between two full years; a partial latest year would look like a fall.
       CASE WHEN months = 12 AND LAG(months) OVER (ORDER BY year) = 12
            THEN ROUND(100 * (value / LAG(value) OVER (ORDER BY year) - 1), 1) END AS yoy_pct,
       CASE WHEN year < 2022 THEN 'before' WHEN year = 2022 THEN 'signed' ELSE 'after' END AS chips_act
FROM yearly
ORDER BY year;

-- name: 2. Equipment vs chip imports, indexed to 2021 = 100 (full years only)
WITH yearly AS (
    SELECT year,
           SUM(value) FILTER (WHERE hs = '8486') AS equipment,
           SUM(value) FILTER (WHERE hs IN ('8541', '8542')) AS chips
    FROM trade
    WHERE flow = 'imports'
    GROUP BY year
    HAVING COUNT(DISTINCT month) = 12
),
base AS (SELECT equipment AS e0, chips AS c0 FROM yearly WHERE year = 2021)
SELECT year,
       ROUND(100 * equipment / e0) AS equipment_index,
       ROUND(100 * chips / c0) AS chips_index,
       ROUND(100 * equipment / e0) - ROUND(100 * chips / c0) AS equipment_minus_chips
FROM yearly, base
ORDER BY year;

-- name: 3. Which suppliers drove the change: 24 months before, 24 months after, latest 24 months
WITH periods AS (
    SELECT * FROM (VALUES
        ('a_before', DATE '2020-08-01', DATE '2022-07-01'),
        ('b_after',  DATE '2022-09-01', DATE '2024-08-01')) AS p(period, first_month, last_month)
    UNION ALL
    -- The 24 most recent months in the data, whatever the latest month is.
    SELECT 'c_latest', CAST(MAX(month_start) - INTERVAL 23 MONTH AS DATE), MAX(month_start)
    FROM trade WHERE flow = 'imports' AND hs = '8486'
),
by_country AS (
    SELECT t.country, p.period, SUM(t.value) AS value
    FROM trade t
    JOIN periods p ON t.month_start BETWEEN p.first_month AND p.last_month
    WHERE t.flow = 'imports' AND t.hs = '8486'
    GROUP BY ALL
),
wide AS (
    PIVOT by_country ON period USING SUM(value) GROUP BY country
)
SELECT country,
       ROUND(a_before / 1e9, 2) AS before_bn,
       ROUND(b_after / 1e9, 2) AS after_bn,
       ROUND(c_latest / 1e9, 2) AS latest_bn,
       ROUND((b_after - a_before) / 1e9, 2) AS change_bn,
       ROUND(100 * a_before / SUM(a_before) OVER (), 1) AS before_share,
       ROUND(100 * b_after / SUM(b_after) OVER (), 1) AS after_share
FROM wide
ORDER BY b_after DESC NULLS LAST
LIMIT 10;
