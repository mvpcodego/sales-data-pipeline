-- Вопрос бизнеса: насколько клиенты возвращаются?
-- Доля клиентов с 2+ заказами и средний интервал между заказами.
WITH per_customer AS (
    SELECT customer_id,
           count(*) AS orders,
           extract(epoch FROM (max(created_at) - min(created_at))) / 86400 AS span_days
    FROM orders
    WHERE status <> 'cancelled' AND customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT count(*)                                                              AS customers,
       count(*) FILTER (WHERE orders >= 2)                                   AS repeat_customers,
       round(100.0 * count(*) FILTER (WHERE orders >= 2) / nullif(count(*), 0), 1) AS repeat_share_pct,
       round(avg(span_days / (orders - 1)) FILTER (WHERE orders >= 2), 1)    AS avg_days_between_orders
FROM per_customer;
