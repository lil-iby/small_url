import json
import logging
import sys

from app.observability import JsonFormatter


def test_response_has_request_id_and_keeps_incoming_one(client):
    assert client.get("/healthz").headers["x-request-id"]
    assert client.get("/healthz", headers={"X-Request-ID": "abc123"}).headers["x-request-id"] == "abc123"


def test_metrics_expose_business_and_http_counters(client, auth):
    client.post("/api/links", json={"url": "https://example.com"}, headers=auth)
    client.get("/inconnu", follow_redirects=False)
    body = client.get("/metrics").text
    assert "shortener_links_created_total" in body
    assert 'shortener_redirects_total{result="miss"}' in body
    assert "http_request_duration_seconds_bucket" in body
    # Le label de route est le gabarit, pas la valeur réelle (évite l'explosion de cardinalité).
    assert 'route="/{code}"' in body
    assert "inconnu" not in body


def test_json_formatter_outputs_one_json_line_with_fields():
    record = logging.LogRecord("shortener", logging.INFO, __file__, 1, "evenement", None, None)
    record.fields = {"code": "abc"}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "evenement"
    assert payload["level"] == "INFO"
    assert payload["code"] == "abc"


def test_json_formatter_includes_exceptions():
    try:
        raise ValueError("boum")
    except ValueError:
        record = logging.LogRecord("shortener", logging.ERROR, __file__, 1, "erreur", None, sys.exc_info())
    assert "ValueError" in json.loads(JsonFormatter().format(record))["exception"]
