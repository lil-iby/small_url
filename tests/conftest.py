import os

# Configuration de test définie AVANT l'import de l'application.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BASE_URL"] = "http://testserver"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["API_KEYS"] = "cle-de-test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security import limiter  # noqa: E402

API_KEY = "cle-de-test"


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth():
    return {"X-API-Key": API_KEY}
