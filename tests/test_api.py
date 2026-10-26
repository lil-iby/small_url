def test_healthz_and_readyz(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_create_link_generates_code(client, auth):
    response = client.post("/api/links", json={"url": "https://example.com/une/page"}, headers=auth)
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 7
    assert body["short_url"] == f"http://testserver/{body['code']}"
    assert body["target_url"] == "https://example.com/une/page"
    assert body["clicks"] == 0


def test_create_link_with_custom_code(client, auth):
    response = client.post(
        "/api/links", json={"url": "https://example.com", "custom_code": "demo-1"}, headers=auth
    )
    assert response.status_code == 201
    assert response.json()["code"] == "demo-1"


def test_duplicate_custom_code_returns_409(client, auth):
    payload = {"url": "https://example.com", "custom_code": "doublon"}
    assert client.post("/api/links", json=payload, headers=auth).status_code == 201
    assert client.post("/api/links", json=payload, headers=auth).status_code == 409


def test_redirect_increments_clicks(client, auth):
    code = client.post("/api/links", json={"url": "https://example.com/cible"}, headers=auth).json()["code"]

    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/cible"

    client.get(f"/{code}", follow_redirects=False)
    assert client.get(f"/api/links/{code}").json()["clicks"] == 2


def test_unknown_code_returns_404(client):
    assert client.get("/inconnu", follow_redirects=False).status_code == 404
    assert client.get("/api/links/inconnu").status_code == 404


def test_rejects_dangerous_or_invalid_urls(client, auth):
    for bad_url in ["javascript:alert(1)", "ftp://example.com/fichier", "pas une url", "file:///etc/passwd"]:
        response = client.post("/api/links", json={"url": bad_url}, headers=auth)
        assert response.status_code == 422, bad_url


def test_rejects_too_long_url(client, auth):
    response = client.post("/api/links", json={"url": "https://example.com/" + "a" * 2100}, headers=auth)
    assert response.status_code == 422


def test_rejects_reserved_and_malformed_custom_codes(client, auth):
    for bad_code in ["api", "metrics", "readyz", "ab", "code avec espace", "a/b"]:
        response = client.post(
            "/api/links", json={"url": "https://example.com", "custom_code": bad_code}, headers=auth
        )
        assert response.status_code == 422, bad_code


def test_blocks_destination_pointing_to_the_service_itself(client, auth):
    response = client.post("/api/links", json={"url": "http://testserver/abc"}, headers=auth)
    assert response.status_code == 422
