"""Общие утилиты. Нормализация телефона используется и в ETL, и в миграции 0002
(там продублирована на SQL), поэтому правило одно и то же."""

from __future__ import annotations

import re


def normalize_phone(raw: str | None) -> str | None:
    """'8 (900) 000-00-01' / '79000000001' -> '+79000000001'."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return "+" + digits
