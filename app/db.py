from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# En SQLite en mémoire (tests), on garde une seule connexion partagée.
_poolclass = StaticPool if settings.database_url.endswith(":memory:") else None

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    **({"poolclass": _poolclass} if _poolclass else {}),
    pool_pre_ping=not _is_sqlite,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
