"""Начальная схема: товары, комплекты, состав, клиенты, заказы, позиции, курсы, журнал загрузок

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(80)),
        sa.Column("series", sa.String(80)),
        sa.Column("price_retail", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stock", sa.Integer, nullable=False, server_default="0"),
        sa.Column("specs", sa.JSON),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.create_table(
        "kits",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kit_code", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("car_title", sa.String(160)),
        sa.Column("price_retail", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_kits_kit_code", "kits", ["kit_code"], unique=True)

    op.create_table(
        "kit_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kit_id", sa.Integer, sa.ForeignKey("kits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_sku", sa.String(64), sa.ForeignKey("products.sku"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("kit_id", "role", name="uq_kit_items_kit_role"),
    )
    op.create_index("ix_kit_items_kit_id", "kit_items", ["kit_id"])
    op.create_index("ix_kit_items_product_sku", "kit_items", ["product_sku"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("name", sa.String(160)),
        sa.Column("city", sa.String(80)),
        # phone_normalized добавляется миграцией 0002
    )
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_order_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id")),
        sa.Column("city", sa.String(80)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_source_order_id", "orders", ["source_order_id"], unique=True)
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer, nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("price", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("order_id", "line_no", name="uq_order_items_line"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_sku", "order_items", ["sku"])

    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("char_code", sa.String(3), nullable=False),
        sa.Column("nominal", sa.Integer, nullable=False, server_default="1"),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("rate_date", sa.String(10), nullable=False),
        sa.UniqueConstraint("char_code", "rate_date", name="uq_fx_code_date"),
    )
    op.create_index("ix_fx_rates_char_code", "fx_rates", ["char_code"])

    op.create_table(
        "etl_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("rows_in", sa.Integer, nullable=False, server_default="0"),
        sa.Column("inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notes", sa.String(500)),
    )
    op.create_index("ix_etl_runs_source", "etl_runs", ["source"])


def downgrade() -> None:
    for table in (
        "etl_runs", "fx_rates", "order_items", "orders",
        "customers", "kit_items", "kits", "products",
    ):
        op.drop_table(table)
