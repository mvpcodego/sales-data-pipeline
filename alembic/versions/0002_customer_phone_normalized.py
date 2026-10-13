"""Нормализованный телефон клиента: добавить поле и заполнить существующие строки

Миграция написана руками. Показывает реальный приём: добавить колонку в таблицу
с данными и сразу привести старые строки в порядок одним UPDATE, тем же правилом,
что применяет ETL (digits-only, код страны +7).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("phone_normalized", sa.String(32)))

    # Заполняем существующие строки тем же правилом, что в pipeline.util.normalize_phone:
    # оставляем цифры; 11 цифр с ведущей 7/8 и 10 цифр -> '+7XXXXXXXXXX'; иначе '+<цифры>'.
    op.execute(
        r"""
        UPDATE customers
        SET phone_normalized = CASE
            WHEN digits = '' THEN NULL
            WHEN length(digits) = 11 AND left(digits, 1) IN ('7', '8') THEN '+7' || right(digits, 10)
            WHEN length(digits) = 10 THEN '+7' || digits
            ELSE '+' || digits
        END
        FROM (
            SELECT id, regexp_replace(phone, '\D', '', 'g') AS digits
            FROM customers
        ) AS src
        WHERE customers.id = src.id
        """
    )

    op.create_index("ix_customers_phone_normalized", "customers", ["phone_normalized"])


def downgrade() -> None:
    op.drop_index("ix_customers_phone_normalized", table_name="customers")
    op.drop_column("customers", "phone_normalized")
