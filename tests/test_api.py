def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_link_generates_code(client):
    response = client.post("/api/links", json={"url": "https://example.com/une/page"})
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 7
    assert body["short_url"] == f"http://testserver/{body['code']}"
    assert body["target_url"] == "https://example.com/une/page"
    assert body["clicks"] == 0


def test_create_link_with_custom_code(client):
    response = client.post("/api/links", json={"url": "https://example.com", "custom_code": "demo-1"})
    assert response.status_code == 201
    assert response.json()["code"] == "demo-1"


def test_duplicate_custom_code_returns_409(client):
    payload = {"url": "https://example.com", "custom_code": "doublon"}
    assert client.post("/api/links", json=payload).status_code == 201
    assert client.post("/api/links", json=payload).status_code == 409


def test_redirect_increments_clicks(client):
    code = client.post("/api/links", json={"url": "https://example.com/cible"}).json()["code"]

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/cible"

    client.get(f"/{code}", follow_redirects=False)
    stats = client.get(f"/api/links/{code}").json()
    assert stats["clicks"] == 2


def test_unknown_code_returns_404(client):
    assert client.get("/inconnu", follow_redirects=False).status_code == 404
    assert client.get("/api/links/inconnu").status_code == 404


def test_rejects_dangerous_or_invalid_urls(client):
    for bad_url in ["javascript:alert(1)", "ftp://example.com/fichier", "pas une url", "file:///etc/passwd"]:
        response = client.post("/api/links", json={"url": bad_url})
        assert response.status_code == 422, bad_url


def test_rejects_reserved_and_malformed_custom_codes(client):
    for bad_code in ["api", "metrics", "ab", "code avec espace", "a/b"]:
        response = client.post("/api/links", json={"url": "https://example.com", "custom_code": bad_code})
        assert response.status_code == 422, bad_code


def test_metrics_endpoint_exposes_counters(client):
    client.post("/api/links", json={"url": "https://example.com"})
    body = client.get("/metrics").text
    assert "shortener_links_created_total" in body
    assert "shortener_redirects_total" in body
