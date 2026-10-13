-- Вопрос бизнеса: кто лучшие клиенты, кого удерживать, кто уходит?
-- R — давность последнего заказа, F — число заказов, M — сумма. NTILE(5) по каждому измерению.
WITH base AS (
    SELECT c.id,
           c.name,
           c.phone_normalized,
           max(o.created_at) AS last_order,
           count(o.id)       AS frequency,
           sum(o.total)      AS monetary
    FROM customers c
    JOIN orders o ON o.customer_id = c.id AND o.status <> 'cancelled'
    GROUP BY c.id, c.name, c.phone_normalized
),
scored AS (
    SELECT *,
           ntile(5) OVER (ORDER BY last_order) AS r,  -- более свежие попадают в старшие тайлы
           ntile(5) OVER (ORDER BY frequency)  AS f,
           ntile(5) OVER (ORDER BY monetary)   AS m
    FROM base
)
SELECT name,
       phone_normalized,
       last_order::date AS last_order,
       frequency,
       monetary,
       r, f, m,
       CASE
           WHEN r >= 4 AND f >= 4 AND m >= 4 THEN 'Чемпионы'
           WHEN r >= 4 AND f >= 3            THEN 'Лояльные'
           WHEN r >= 4 AND f <= 2            THEN 'Новички'
           WHEN r <= 2 AND f >= 4            THEN 'Под угрозой'
           WHEN r <= 2 AND m >= 4            THEN 'Спящие ценные'
           WHEN r <= 2                       THEN 'Потерянные'
           ELSE 'Средние'
       END AS segment
FROM scored
ORDER BY monetary DESC;
