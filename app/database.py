from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings, resolve_database_url


class Base(DeclarativeBase):
    pass


def create_db_engine(settings: Settings, *, read_only: bool = False):
    url = resolve_database_url(settings)
    kwargs = {"future": True}
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    if url.startswith("duckdb") and read_only:
        connect_args["read_only"] = True
    if url.startswith("mysql"):
        kwargs["pool_pre_ping"] = True
        connect_args["local_infile"] = 1
    if connect_args:
        kwargs["connect_args"] = connect_args
    return create_engine(url, **kwargs)


def create_session_factory(settings: Settings, *, read_only: bool = False):
    engine = create_db_engine(settings, read_only=read_only)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(session_factory):
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
