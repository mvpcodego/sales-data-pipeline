"""Конфигурация из окружения. Секреты только в .env, не в коде."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Переменная {name} не задана. Скопируйте .env.example в .env и заполните."
        )
    return value


def _path(name: str, default: str) -> Path:
    raw = os.environ.get(name, default)
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


DATABASE_URL = _require("DATABASE_URL")
CRM_JSON_PATH = _path("CRM_JSON_PATH", "data/crm_export.json")
PRICE_CSV_PATH = _path("PRICE_CSV_PATH", "data/price_list.csv")
CBR_CACHE_PATH = _path("CBR_CACHE_PATH", "data/cbr_rates_cache.xml")
CBR_URL = os.environ.get("CBR_URL", "https://www.cbr.ru/scripts/XML_daily.asp")
SQL_DIR = ROOT / "sql"
REPORT_PATH = ROOT / "report.xlsx"
