-- Вопрос бизнеса: на сколько дней хватит остатка при текущей скорости продаж
-- и что заказывать первым? Расход считаем по складским позициям (с раскрытием комплектов).
WITH period AS (
    SELECT greatest(extract(day FROM (max(created_at) - min(created_at)))::numeric, 1) AS days
    FROM orders WHERE status <> 'cancelled'
),
sold AS (
    SELECT ki.product_sku AS sku, oi.quantity * ki.quantity AS qty
    FROM order_items oi
    JOIN orders o     ON o.id = oi.order_id AND o.status <> 'cancelled'
    JOIN kits k       ON k.kit_code = oi.sku
    JOIN kit_items ki ON ki.kit_id = k.id
    WHERE oi.kind = 'kit'
    UNION ALL
    SELECT oi.sku, oi.quantity
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id AND o.status <> 'cancelled'
    WHERE oi.kind = 'product'
),
agg AS (
    SELECT p.sku, p.title, p.stock, sum(s.qty) AS units_sold
    FROM sold s JOIN products p ON p.sku = s.sku
    GROUP BY p.sku, p.title, p.stock
)
SELECT a.sku,
       a.title,
       a.stock,
       a.units_sold,
       round(a.units_sold / (SELECT days FROM period), 3) AS per_day,
       CASE WHEN a.units_sold > 0
            THEN round(a.stock / (a.units_sold / (SELECT days FROM period)), 1)
            ELSE NULL END AS days_left
FROM agg a
ORDER BY days_left NULLS LAST;  -- что кончится раньше — выше, его заказывать первым
