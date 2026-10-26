"""Tests d'intégration contre un vrai PostgreSQL.

Ignorés si TEST_POSTGRES_URL n'est pas défini. En CI, un service PostgreSQL est démarré
et la variable est renseignée.
"""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import services
from app.db import Base
from app.models import Link

POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="TEST_POSTGRES_URL non défini")


@pytest.fixture()
def session_factory():
    engine = create_engine(POSTGRES_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_concurrent_clicks_are_all_counted(session_factory):
    with session_factory() as db:
        link = services.create_link(
            db, "https://example.com", custom_code=None, code_length=7, blocked_domains=[]
        )
        code = link.code

    def click(_):
        with session_factory() as db:
            services.register_click(db, code)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(click, range(200)))

    with session_factory() as db:
        assert db.scalar(select(Link.clicks).where(Link.code == code)) == 200
