"""Сверка источника с базой и проверки качества данных.
Запуск: python -m pipeline.check

Печатает по каждой таблице «было в источнике — дошло — выпало» и отдельно
проверки качества: дубли клиентов по телефону, заказы без клиента, пустые телефоны.
"""

from __future__ import annotations

from sqlalchemy import func, select

from pipeline import sources
from pipeline.db import session_scope
from pipeline.models import Customer, Kit, KitItem, Order, OrderItem, Product


def _source_counts(crm: dict) -> dict[str, int]:
    kit_items = sum(
        1 for k in crm["kits"] for f in ("head_unit_id", "frame_id", "wiring_id", "starter_kit_id") if k.get(f)
    )
    unique_phones = {
        (o.get("customer") or {}).get("phone", "").strip()
        for o in crm["orders"]
        if (o.get("customer") or {}).get("phone", "").strip()
    }
    return {
        "products": len(crm["parts"]),
        "kits": len(crm["kits"]),
        "kit_items": kit_items,
        "customers": len(unique_phones),
        "orders": len(crm["orders"]),
        "order_items": sum(len(o.get("items", [])) for o in crm["orders"]),
    }


def run() -> int:
    crm = sources.load_crm()
    src = _source_counts(crm)

    with session_scope() as session:
        db = {
            "products": session.scalar(select(func.count()).select_from(Product)),
            "kits": session.scalar(select(func.count()).select_from(Kit)),
            "kit_items": session.scalar(select(func.count()).select_from(KitItem)),
            "customers": session.scalar(select(func.count()).select_from(Customer)),
            "orders": session.scalar(select(func.count()).select_from(Order)),
            "order_items": session.scalar(select(func.count()).select_from(OrderItem)),
        }

        dup_phones = session.execute(
            select(Customer.phone, func.count())
            .group_by(Customer.phone)
            .having(func.count() > 1)
        ).all()
        orders_no_customer = session.scalar(
            select(func.count()).select_from(Order).where(Order.customer_id.is_(None))
        )
        empty_phones = session.scalar(
            select(func.count()).select_from(Customer).where(
                (Customer.phone_normalized.is_(None)) | (Customer.phone == "")
            )
        )

    print("Сверка источник → база (было · дошло · выпало):")
    total_lost = 0
    for table in ("products", "kits", "kit_items", "customers", "orders", "order_items"):
        was, got = src[table], db[table]
        lost = was - got
        total_lost += max(lost, 0)
        mark = "ok" if lost == 0 else "ВНИМАНИЕ"
        print(f"  {table:<13} {was:>5} · {got:>5} · {lost:>4}  [{mark}]")

    print("\nКачество данных:")
    print(f"  дубли клиентов по телефону : {len(dup_phones)}")
    print(f"  заказы без клиента         : {orders_no_customer}")
    print(f"  пустые телефоны            : {empty_phones}")

    problems = total_lost + len(dup_phones) + orders_no_customer + empty_phones
    if problems == 0:
        print("\nИтог: данные целостны, потерь и аномалий нет.")
    else:
        print(f"\nИтог: есть что проверить (суммарно отклонений: {problems}).")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
