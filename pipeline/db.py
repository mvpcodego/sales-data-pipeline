"""Движок и сессии SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pipeline.config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)
SessionFactory = sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Сессия с автокоммитом по выходу и откатом при ошибке."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
