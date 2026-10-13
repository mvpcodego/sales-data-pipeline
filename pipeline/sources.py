"""Чтение трёх источников: CRM-выгрузка (JSON), прайс менеджера (CSV),
курсы ЦБ (внешний API с офлайн-кэшем)."""

from __future__ import annotations

import csv
import json
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pipeline.config import CBR_CACHE_PATH, CBR_URL, CRM_JSON_PATH, PRICE_CSV_PATH


def load_crm() -> dict:
    """CRM-выгрузка: заказы, клиенты, товары, комплекты."""
    with open(CRM_JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_price_csv() -> list[dict]:
    """Прайс от менеджера: sku;name;price (разделитель ';')."""
    rows: list[dict] = []
    with open(PRICE_CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            rows.append(row)
    return rows


@dataclass
class FxResult:
    date: str
    rates: list[dict] = field(default_factory=list)
    from_cache: bool = False
    note: str = ""


_WANTED = {"USD", "EUR", "CNY"}


def _parse_cbr_xml(raw: bytes) -> FxResult:
    # ЦБ отдаёт windows-1251; парсим из байтов, чтобы кодировка бралась из пролога XML.
    root = ET.fromstring(raw)
    date = root.attrib.get("Date", "")
    iso = datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d") if date else ""
    rates = []
    for v in root.findall("Valute"):
        code = (v.findtext("CharCode") or "").strip()
        if code not in _WANTED:
            continue
        nominal = int((v.findtext("Nominal") or "1").replace("\xa0", ""))
        value = float((v.findtext("Value") or "0").replace("\xa0", "").replace(",", "."))
        rates.append({"char_code": code, "nominal": nominal, "value": value, "rate_date": iso})
    return FxResult(date=iso, rates=rates)


def load_fx() -> FxResult:
    """Курсы ЦБ. Пробуем онлайн; при недоступности сети — последний кэш.
    При удачном онлайн-запросе кэш обновляется. Загрузка не падает без сети."""
    try:
        req = urllib.request.Request(CBR_URL, headers={"User-Agent": "sales-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        Path(CBR_CACHE_PATH).write_bytes(raw)  # обновляем кэш
        result = _parse_cbr_xml(raw)
        result.note = "онлайн, кэш обновлён"
        return result
    except Exception as exc:  # noqa: BLE001 — любой сбой сети уводит в офлайн-режим
        if Path(CBR_CACHE_PATH).exists():
            result = _parse_cbr_xml(Path(CBR_CACHE_PATH).read_bytes())
            result.from_cache = True
            result.note = f"офлайн, из кэша ({type(exc).__name__})"
            return result
        return FxResult(date="", note=f"нет сети и нет кэша: {exc}")
