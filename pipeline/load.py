"""ETL: загрузка трёх источников в базу. Запуск: python -m pipeline.load

Идемпотентность — через INSERT ... ON CONFLICT DO UPDATE по естественному ключу.
Повторный запуск не создаёт дублей. Каждый источник пишет строку в etl_runs
(сколько пришло, вставлено, обновлено, отброшено и почему).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from pipeline import sources
from pipeline.db import session_scope
from pipeline.models import (
    Customer,
    EtlRun,
    FxRate,
    Kit,
    KitItem,
    Order,
    OrderItem,
    Product,
)
from pipeline.util import normalize_phone

ROLE_FIELDS = [
    ("head_unit_id", "head_unit"),
    ("frame_id", "frame"),
    ("wiring_id", "wiring"),
    ("starter_kit_id", "starter_kit"),
]


def _now() -> datetime:
    return datetime.now(UTC)


def _dt(value):
    """ISO-строка ('...Z') в aware datetime. None и datetime пропускаем как есть."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _upsert(session: Session, model, rows: list[dict], index_elements: list[str], update_cols: list[str]):
    """Upsert пачкой через ON CONFLICT DO UPDATE. Возвращает (inserted, updated).

    Считаем вставки и обновления по системному полю Postgres xmax:
    у свежевставленной строки xmax = 0, у обновлённой — id текущей транзакции.
    """
    if not rows:
        return 0, 0
    stmt = pg_insert(model).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=index_elements,
        set_={c: stmt.excluded[c] for c in update_cols},
    ).returning(literal_column("(xmax = 0)"))
    inserted = updated = 0
    for is_insert in session.execute(stmt).scalars():
        if is_insert:
            inserted += 1
        else:
            updated += 1
    return inserted, updated


def _log(session: Session, source: str, started: datetime, rows_in: int, ins: int, upd: int, skip: int, notes: str):
    session.add(
        EtlRun(
            source=source,
            started_at=started,
            finished_at=_now(),
            rows_in=rows_in,
            inserted=ins,
            updated=upd,
            skipped=skip,
            notes=notes[:500],
        )
    )


def load_products(session: Session, crm: dict) -> None:
    started = _now()
    rows = [
        {
            "sku": p["sku"],
            "type": p["type"],
            "title": p["title"],
            "brand": p.get("brand"),
            "series": p.get("series"),
            "price_retail": p.get("price_retail") or 0,
            "stock": p.get("stock") or 0,
            "specs": p.get("specs"),
            "archived": bool(p.get("archived")),
            "source_updated_at": _dt(p.get("updated_at")),
        }
        for p in crm["parts"]
    ]
    ins, upd = _upsert(
        session, Product, rows, ["sku"],
        ["type", "title", "brand", "series", "price_retail", "stock", "specs", "archived", "source_updated_at"],
    )
    _log(session, "crm:products", started, len(rows), ins, upd, 0, "товары из CRM-выгрузки")


def load_kits(session: Session, crm: dict) -> None:
    started = _now()
    kit_rows = [
        {
            "kit_code": f"kit-{k['id']}",
            "title": k["title"],
            "car_title": k.get("title", "").split(" + ")[0] or None,
            "price_retail": k.get("price_retail") or 0,
            "is_default": bool(k.get("is_default")),
        }
        for k in crm["kits"]
    ]
    ins, upd = _upsert(session, Kit, kit_rows, ["kit_code"], ["title", "car_title", "price_retail", "is_default"])
    _log(session, "crm:kits", started, len(kit_rows), ins, upd, 0, "комплекты из CRM-выгрузки")

    # Состав комплектов: разворачиваем 4 ссылки на товары в строки kit_items.
    started = _now()
    code_to_id = dict(session.execute(select(Kit.kit_code, Kit.id)).all())
    part_by_id = {p["id"]: p["sku"] for p in crm["parts"]}
    item_rows: list[dict] = []
    skipped = 0
    for k in crm["kits"]:
        kit_id = code_to_id[f"kit-{k['id']}"]
        for field_name, role in ROLE_FIELDS:
            pid = k.get(field_name)
            sku = part_by_id.get(pid) if pid else None
            if not sku:
                skipped += 1
                continue
            item_rows.append({"kit_id": kit_id, "product_sku": sku, "role": role, "quantity": 1})
    ins, upd = _upsert(session, KitItem, item_rows, ["kit_id", "role"], ["product_sku", "quantity"])
    _log(session, "crm:kit_items", started, len(item_rows) + skipped, ins, upd, skipped,
         "состав комплектов" + (f"; {skipped} без ссылки на товар" if skipped else ""))


def load_customers(session: Session, crm: dict) -> int:
    """Дедупликация клиентов по телефону. Возвращает число отброшенных (пустой телефон)."""
    started = _now()
    by_phone: dict[str, dict] = {}
    skipped = 0
    for o in crm["orders"]:
        c = o.get("customer") or {}
        phone = (c.get("phone") or "").strip()
        if not phone:
            skipped += 1
            continue
        by_phone.setdefault(phone, {
            "phone": phone,
            "phone_normalized": normalize_phone(phone),
            "name": c.get("name"),
            "city": c.get("city"),
        })
    rows = list(by_phone.values())
    ins, upd = _upsert(session, Customer, rows, ["phone"], ["phone_normalized", "name", "city"])
    _log(session, "crm:customers", started, len(rows) + skipped, ins, upd, skipped,
         "клиенты, дедуп по телефону" + (f"; {skipped} заказов без телефона" if skipped else ""))
    return skipped


def load_orders(session: Session, crm: dict) -> None:
    started = _now()
    phone_to_id = dict(session.execute(select(Customer.phone, Customer.id)).all())
    order_rows = []
    for o in crm["orders"]:
        c = o.get("customer") or {}
        phone = (c.get("phone") or "").strip()
        order_rows.append({
            "source_order_id": o["id"],
            "customer_id": phone_to_id.get(phone),
            "city": c.get("city"),
            "status": o.get("status", "new"),
            "total": o.get("total") or 0,
            "created_at": _dt(o["created_at"]),
        })
    ins, upd = _upsert(session, Order, order_rows, ["source_order_id"],
                       ["customer_id", "city", "status", "total", "created_at"])
    _log(session, "crm:orders", started, len(order_rows), ins, upd, 0, "заказы из CRM-выгрузки")

    # Позиции заказов: kit-NN или sku товара. Переливаем идемпотентно по (order_id, line_no).
    started = _now()
    src_to_id = dict(session.execute(select(Order.source_order_id, Order.id)).all())
    item_rows = []
    for o in crm["orders"]:
        oid = src_to_id[o["id"]]
        for i, it in enumerate(o.get("items", []), start=1):
            sku = it["sku"]
            item_rows.append({
                "order_id": oid,
                "line_no": i,
                "sku": sku,
                "kind": "kit" if sku.startswith("kit-") else "product",
                "title": it.get("title"),
                "price": it.get("price") or 0,
                "quantity": it.get("quantity") or 1,
            })
    ins, upd = _upsert(session, OrderItem, item_rows, ["order_id", "line_no"],
                       ["sku", "kind", "title", "price", "quantity"])
    _log(session, "crm:order_items", started, len(item_rows), ins, upd, 0, "позиции заказов (комплекты и допы)")


def load_price_csv(session: Session) -> None:
    """Прайс менеджера: обновляем только цену товара. Неизвестные sku — в отброшенные."""
    started = _now()
    rows = sources.load_price_csv()
    known = set(session.execute(select(Product.sku)).scalars())
    updates = []
    skipped = 0
    bad_examples = []
    for r in rows:
        sku = (r.get("sku") or "").strip()
        if sku not in known:
            skipped += 1
            if len(bad_examples) < 3:
                bad_examples.append(sku)
            continue
        updates.append({"sku": sku, "price_retail": int(float(r["price"]))})
    # upsert по sku: товар уже есть, поэтому это обновление цены
    ins, upd = _upsert(session, Product, _fill_price_defaults(session, updates), ["sku"], ["price_retail"])
    note = "прайс от менеджера → обновление цен"
    if skipped:
        note += f"; {skipped} строк с неизвестным sku ({', '.join(bad_examples)})"
    _log(session, "price_csv", started, len(rows), ins, upd, skipped, note)


def _fill_price_defaults(session: Session, updates: list[dict]) -> list[dict]:
    """ON CONFLICT требует валидных NOT NULL полей при вставке. Цена обновляет существующие
    строки, но на всякий случай добавляем обязательные поля-заглушки для несуществующих sku
    (их тут нет, т.к. неизвестные уже отброшены) — страхует от падения INSERT."""
    out = []
    for u in updates:
        out.append({"sku": u["sku"], "type": "unknown", "title": u["sku"], "price_retail": u["price_retail"]})
    return out


def load_fx(session: Session) -> None:
    started = _now()
    fx = sources.load_fx()
    rows = [
        {"char_code": r["char_code"], "nominal": r["nominal"], "value": r["value"], "rate_date": r["rate_date"]}
        for r in fx.rates
    ]
    ins = upd = 0
    if rows:
        ins, upd = _upsert(session, FxRate, rows, ["char_code", "rate_date"], ["nominal", "value"])
    _log(session, "cbr_fx", started, len(rows), ins, upd, 0, f"курсы ЦБ на {fx.date or '—'}: {fx.note}")


def run() -> None:
    crm = sources.load_crm()
    with session_scope() as session:
        load_products(session, crm)
        load_kits(session, crm)
        load_customers(session, crm)
        load_orders(session, crm)
        load_price_csv(session)
        load_fx(session)

    # Короткая сводка последнего запуска в консоль.
    with session_scope() as session:
        runs = session.execute(
            select(EtlRun).order_by(EtlRun.id.desc()).limit(6)
        ).scalars().all()
    print("ETL завершён. Последние загрузки:")
    for r in reversed(runs):
        print(f"  {r.source:<16} пришло {r.rows_in:>4} · +{r.inserted} ~{r.updated} ×{r.skipped}  {r.notes or ''}")


if __name__ == "__main__":
    run()
