import time

import pytest

from app.config import Settings, settings
from app.security import RateLimiter, client_id


def test_create_requires_api_key(client):
    payload = {"url": "https://example.com"}
    assert client.post("/api/links", json=payload).status_code == 401
    assert client.post("/api/links", json=payload, headers={"X-API-Key": "mauvaise"}).status_code == 401


def test_stats_and_redirect_are_public(client, auth):
    code = client.post("/api/links", json={"url": "https://example.com"}, headers=auth).json()["code"]
    assert client.get(f"/api/links/{code}").status_code == 200
    assert client.get(f"/{code}", follow_redirects=False).status_code == 302


def test_security_headers_are_present(client):
    response = client.get("/healthz")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_rate_limit_on_creation(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_create_per_minute", 2)
    payload = {"url": "https://example.com"}
    assert client.post("/api/links", json=payload, headers=auth).status_code == 201
    assert client.post("/api/links", json=payload, headers=auth).status_code == 201
    blocked = client.post("/api/links", json=payload, headers=auth)
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"


def test_rate_limit_on_redirect(client, auth, monkeypatch):
    code = client.post("/api/links", json={"url": "https://example.com"}, headers=auth).json()["code"]
    monkeypatch.setattr(settings, "rate_limit_redirect_per_minute", 1)
    assert client.get(f"/{code}", follow_redirects=False).status_code == 302
    assert client.get(f"/{code}", follow_redirects=False).status_code == 429


def test_blocked_domain_is_refused(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "blocked_domains", "mauvais.example, evil.test")
    for url in ["https://mauvais.example/x", "https://sous.evil.test/y"]:
        assert client.post("/api/links", json={"url": url}, headers=auth).status_code == 422
    assert client.post("/api/links", json={"url": "https://bon.example"}, headers=auth).status_code == 201


def test_rate_limiter_window_expires():
    limiter = RateLimiter()
    assert limiter.allow("k", limit=1, window_seconds=0.05)
    assert not limiter.allow("k", limit=1, window_seconds=0.05)
    time.sleep(0.06)
    assert limiter.allow("k", limit=1, window_seconds=0.05)


def test_client_id_uses_forwarded_header_only_when_trusted(monkeypatch):
    class Request:
        headers = {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}  # noqa: RUF012
        client = type("Client", (), {"host": "10.0.0.1"})()

    assert client_id(Request()) == "10.0.0.1"
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert client_id(Request()) == "203.0.113.9"


def test_production_requires_keys_and_real_database():
    postgres = "postgresql+psycopg://u:p@h/db"
    with pytest.raises(RuntimeError, match="API_KEYS"):
        Settings(environment="production", api_keys="", database_url=postgres).check_production_requirements()
    with pytest.raises(RuntimeError, match="SQLite"):
        Settings(
            environment="production", api_keys="k", database_url="sqlite:///x.db"
        ).check_production_requirements()
    Settings(environment="production", api_keys="k", database_url=postgres).check_production_requirements()
