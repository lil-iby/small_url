import pytest

from app import services
from app.db import SessionLocal
from app.errors import BlockedUrlError, CodeGenerationError, CodeTakenError, LinkNotFoundError


@pytest.fixture()
def db(client):  # `client` crée les tables
    session = SessionLocal()
    yield session
    session.close()


def make(db, url="https://example.com", **kwargs):
    defaults = {"custom_code": None, "code_length": 7, "blocked_domains": []}
    defaults.update(kwargs)
    return services.create_link(db, url, **defaults)


def test_generate_code_has_requested_length_and_alphabet():
    code = services.generate_code(12)
    assert len(code) == 12
    assert set(code) <= set(services.ALPHABET)


def test_codes_are_not_repeated():
    assert len({services.generate_code(7) for _ in range(500)}) == 500


def test_create_and_get_link(db):
    link = make(db)
    assert services.get_link(db, link.code).target_url == "https://example.com"


def test_get_unknown_link_raises(db):
    with pytest.raises(LinkNotFoundError):
        services.get_link(db, "inexistant")


def test_custom_code_collision_raises(db):
    make(db, custom_code="pris")
    with pytest.raises(CodeTakenError):
        make(db, custom_code="pris")


def test_generation_gives_up_after_repeated_collisions(db, monkeypatch):
    make(db, custom_code="fixe123")
    monkeypatch.setattr(services, "generate_code", lambda _: "fixe123")
    with pytest.raises(CodeGenerationError):
        make(db)


def test_blocked_domain_and_subdomain(db):
    with pytest.raises(BlockedUrlError):
        make(db, url="https://evil.test/a", blocked_domains=["evil.test"])
    with pytest.raises(BlockedUrlError):
        make(db, url="https://a.b.evil.test/a", blocked_domains=["evil.test"])
    make(db, url="https://notevil.test/a", blocked_domains=["evil.test"])


def test_register_click_increments(db):
    link = make(db)
    assert services.register_click(db, link.code) == "https://example.com"
    services.register_click(db, link.code)
    db.expire_all()
    assert services.get_link(db, link.code).clicks == 2
