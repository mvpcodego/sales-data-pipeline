"""Общие фикстуры. Тесты требуют поднятой и мигрированной базы; если её нет —
они пропускаются с понятным сообщением, а не падают."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from pipeline.db import engine


def _db_ready() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1 FROM etl_runs LIMIT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_ok():
    if not _db_ready():
        pytest.skip("БД недоступна/не мигрирована. Выполните: alembic upgrade head && python -m pipeline.load")


@pytest.fixture
def conn(db_ok):
    """Соединение в транзакции, которая откатывается после теста — данные не остаются."""
    connection = engine.connect()
    trans = connection.begin()
    try:
        yield connection
    finally:
        trans.rollback()
        connection.close()
