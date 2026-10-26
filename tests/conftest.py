import os

# La base de tests est une SQLite en mémoire, définie AVANT l'import de l'application.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BASE_URL"] = "http://testserver"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
