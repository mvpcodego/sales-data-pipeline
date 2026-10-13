-- Вопрос бизнеса: какие товары дают выручку за последние 90 дней и какова их доля?
-- Выручка — по проданным позициям заказа (комплект продаётся как единица со своей ценой).
WITH recent AS (
    SELECT oi.sku,
           coalesce(oi.title, oi.sku) AS title,
           oi.price * oi.quantity     AS revenue
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id AND o.status <> 'cancelled'
    WHERE o.created_at >= (SELECT max(created_at) FROM orders) - interval '90 days'
),
agg AS (
    SELECT sku, max(title) AS title, sum(revenue) AS revenue
    FROM recent GROUP BY sku
)
SELECT title,
       revenue,
       round(100.0 * revenue / sum(revenue) OVER (), 1) AS share_pct
FROM agg
ORDER BY revenue DESC
LIMIT 10;
