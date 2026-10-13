"""Типизированные модели SQLAlchemy 2.0.

Модель описывает итоговое состояние схемы (как после всех миграций).
Миграция 0001 создаёт схему без customers.phone_normalized,
миграция 0002 добавляет это поле и заполняет существующие строки.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # естественный ключ
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(80))
    series: Mapped[str | None] = mapped_column(String(80))
    price_retail: Mapped[int] = mapped_column(Integer, default=0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    specs: Mapped[dict | None] = mapped_column(JSON)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Kit(Base):
    __tablename__ = "kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kit_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # "kit-47"
    title: Mapped[str] = mapped_column(String(255))
    car_title: Mapped[str | None] = mapped_column(String(160))
    price_retail: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list[KitItem]] = relationship(back_populates="kit", cascade="all, delete-orphan")


class KitItem(Base):
    __tablename__ = "kit_items"
    __table_args__ = (UniqueConstraint("kit_id", "role", name="uq_kit_items_kit_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kit_id: Mapped[int] = mapped_column(ForeignKey("kits.id", ondelete="CASCADE"), index=True)
    product_sku: Mapped[str] = mapped_column(ForeignKey("products.sku"), index=True)
    role: Mapped[str] = mapped_column(String(40))  # head_unit | frame | wiring | starter_kit
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    kit: Mapped[Kit] = relationship(back_populates="items")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # естественный ключ
    phone_normalized: Mapped[str | None] = mapped_column(String(32), index=True)  # добавлено в 0002
    name: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(80))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_order_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)  # естественный ключ
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    city: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(32), index=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (UniqueConstraint("order_id", "line_no", name="uq_order_items_line"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    sku: Mapped[str] = mapped_column(String(64), index=True)  # "kit-47" или sku товара
    kind: Mapped[str] = mapped_column(String(16))  # kit | product
    title: Mapped[str | None] = mapped_column(String(255))
    price: Mapped[int] = mapped_column(Integer, default=0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    order: Mapped[Order] = relationship(back_populates="items")


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("char_code", "rate_date", name="uq_fx_code_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    char_code: Mapped[str] = mapped_column(String(3), index=True)  # USD, EUR, CNY
    nominal: Mapped[int] = mapped_column(Integer, default=1)
    value: Mapped[float] = mapped_column(Numeric(12, 4))  # рублей за nominal единиц
    rate_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD из ответа ЦБ


class EtlRun(Base):
    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_in: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(String(500))
