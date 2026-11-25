WITH running AS (
  SELECT customer, day,
         SUM(amount) OVER (PARTITION BY customer ORDER BY day, id) AS running_total
  FROM orders
),
first_hit AS (
  SELECT customer, MIN(day) AS day
  FROM running
  WHERE running_total >= 100
  GROUP BY customer
)
SELECT customer, day
FROM first_hit
ORDER BY customer;
