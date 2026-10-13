-- Вопрос бизнеса: как росла выручка по месяцам и какой накопленный итог?
-- Отменённые заказы в выручку не включаем. Накопительный итог — оконной функцией.
WITH monthly AS (
    SELECT date_trunc('month', created_at)::date AS month,
           sum(total)                            AS revenue,
           count(*)                              AS orders
    FROM orders
    WHERE status <> 'cancelled'
    GROUP BY 1
)
SELECT month,
       revenue,
       orders,
       sum(revenue) OVER (ORDER BY month) AS revenue_cumulative
FROM monthly
ORDER BY month;
