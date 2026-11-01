-- Who supplies the most? Top 3 integrated circuit (HS 8542) suppliers per full year,
-- with each one's year-over-year growth.

-- name: Top 3 integrated circuit suppliers per year
WITH yearly AS (
    SELECT year, country, SUM(value) AS value
    FROM trade
    WHERE flow = 'imports' AND hs = '8542'
      AND year IN (SELECT year FROM trade GROUP BY year HAVING COUNT(DISTINCT month) = 12)
    GROUP BY ALL
)
SELECT year,
       RANK() OVER (PARTITION BY year ORDER BY value DESC) AS rnk,
       country,
       ROUND(value / 1e9, 2) AS usd_bn,
       ROUND(100 * value / SUM(value) OVER (PARTITION BY year), 1) AS share_pct,
       ROUND(100 * (value / LAG(value) OVER (PARTITION BY country ORDER BY year) - 1), 1) AS yoy_pct
FROM yearly
QUALIFY rnk <= 3
ORDER BY year, rnk;
