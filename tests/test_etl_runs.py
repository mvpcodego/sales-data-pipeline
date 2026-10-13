"""Отброшенные записи попадают в журнал etl_runs с причиной."""
from __future__ import annotations

from sqlalchemy import select

from pipeline import load
from pipeline.db import SessionFactory
from pipeline.models import EtlRun


def test_unknown_sku_is_skipped_and_logged(db_ok, monkeypatch, tmp_path):
    bad = tmp_path / "price.csv"
    bad.write_text(
        "sku;name;price\nNOPE-404;Несуществующий;1000\nHU-AURIO-S1-9;Реальный;26000\n",
        encoding="utf-8",
    )
    # sources читает путь из своего пространства имён — патчим именно его
    monkeypatch.setattr("pipeline.sources.PRICE_CSV_PATH", bad)

    session = SessionFactory()
    try:
        load.load_price_csv(session)
        run = session.execute(
            select(EtlRun).where(EtlRun.source == "price_csv").order_by(EtlRun.id.desc())
        ).scalars().first()
        assert run is not None
        assert run.skipped >= 1
        assert "NOPE-404" in (run.notes or "")
    finally:
        session.rollback()  # ничего не оставляем в базе
        session.close()
