"""Повторная загрузка не меняет число строк (идемпотентность upsert)."""
from __future__ import annotations

from sqlalchemy import text

from pipeline import load
from pipeline.db import engine

TABLES = ("products", "kits", "kit_items", "customers", "orders", "order_items")


def _counts() -> dict[str, int]:
    with engine.connect() as c:
        return {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TABLES}


def test_second_load_adds_no_rows(db_ok):
    load.run()            # приводим базу к загруженному состоянию
    before = _counts()
    load.run()            # второй прогон того же источника
    after = _counts()
    assert before == after, f"появились дубли: {before} -> {after}"
