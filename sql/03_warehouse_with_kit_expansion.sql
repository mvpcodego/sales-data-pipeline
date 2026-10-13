-- Вопрос бизнеса: сколько РЕАЛЬНЫХ складских позиций продано?
-- В заказах лежат артикулы комплектов (kit-NN), а склад считается по позициям.
-- Без раскрытия комплекта в состав (ГУ + рамка + проводка + набор) половина расхода «не видна».
WITH sold AS (
    -- позиции-комплекты разворачиваем в состав
    SELECT ki.product_sku AS sku,
           oi.quantity * ki.quantity AS qty
    FROM order_items oi
    JOIN orders o     ON o.id = oi.order_id AND o.status <> 'cancelled'
    JOIN kits k       ON k.kit_code = oi.sku
    JOIN kit_items ki ON ki.kit_id = k.id
    WHERE oi.kind = 'kit'
    UNION ALL
    -- позиции-товары (допы) идут как есть
    SELECT oi.sku, oi.quantity
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id AND o.status <> 'cancelled'
    WHERE oi.kind = 'product'
)
SELECT p.sku,
       p.title,
       p.type,
       sum(s.qty) AS units_sold,
       p.stock
FROM sold s
JOIN products p ON p.sku = s.sku
GROUP BY p.sku, p.title, p.type, p.stock
ORDER BY units_sold DESC;
