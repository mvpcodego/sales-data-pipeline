"""Раскрытие комплектов в состав даёт правильные количества на ручном примере.

Комплект из двух позиций продан в заказе с количеством 2 — значит каждой
складской позиции должно уйти по 2 штуки.
"""
from __future__ import annotations

from sqlalchemy import text

from pipeline.config import SQL_DIR


def test_kit_expands_with_quantity(conn):
    conn.execute(text(
        "INSERT INTO products(sku,type,title,price_retail,stock) "
        "VALUES ('T-HU','head_unit','Тест ГУ',1,0),('T-FR','frame','Тест рамка',1,0)"
    ))
    conn.execute(text("INSERT INTO kits(kit_code,title,price_retail) VALUES ('kit-9001','Тест-комплект',1)"))
    kit_id = conn.execute(text("SELECT id FROM kits WHERE kit_code='kit-9001'")).scalar()
    conn.execute(
        text("INSERT INTO kit_items(kit_id,product_sku,role,quantity) "
             "VALUES (:k,'T-HU','head_unit',1),(:k,'T-FR','frame',1)"),
        {"k": kit_id},
    )
    conn.execute(text("INSERT INTO customers(phone) VALUES ('70000000999')"))
    cid = conn.execute(text("SELECT id FROM customers WHERE phone='70000000999'")).scalar()
    conn.execute(
        text("INSERT INTO orders(source_order_id,customer_id,status,total,created_at) "
             "VALUES (999001,:c,'delivered',2,now())"),
        {"c": cid},
    )
    oid = conn.execute(text("SELECT id FROM orders WHERE source_order_id=999001")).scalar()
    conn.execute(
        text("INSERT INTO order_items(order_id,line_no,sku,kind,title,price,quantity) "
             "VALUES (:o,1,'kit-9001','kit','Тест-комплект',2,2)"),
        {"o": oid},
    )

    sql = (SQL_DIR / "03_warehouse_with_kit_expansion.sql").read_text(encoding="utf-8")
    result = {r[0]: r[3] for r in conn.execute(text(sql)).fetchall() if r[0] in ("T-HU", "T-FR")}
    assert result == {"T-HU": 2, "T-FR": 2}
