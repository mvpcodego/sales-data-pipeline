"""Генерация CSV-прайса «от менеджера» из CRM-выгрузки: те же товары с изменёнными
ценами (±8%, округление до 10 ₽). Детерминированно (seed=42). Запуск:
    python scripts/make_price_csv.py
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRM = ROOT / "data" / "crm_export.json"
OUT = ROOT / "data" / "price_list.csv"


def main() -> None:
    data = json.loads(CRM.read_text(encoding="utf-8"))
    rnd = random.Random(42)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["sku", "name", "price"])
        for p in data["parts"]:
            base = p.get("price_retail") or 0
            new = int(round(base * (1 + rnd.uniform(-0.08, 0.08)) / 10)) * 10 if base else 0
            w.writerow([p["sku"], p["title"], new])
    print(f"Готово: {OUT.relative_to(ROOT)} ({len(data['parts'])} строк)")


if __name__ == "__main__":
    main()
