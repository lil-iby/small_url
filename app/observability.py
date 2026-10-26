"""Observabilité : journaux JSON structurés, identifiant de requête, métriques Prometheus."""

import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime

from fastapi import Request
from prometheus_client import Counter, Histogram

logger = logging.getLogger("shortener")

LINKS_CREATED = Counter("shortener_links_created_total", "Nombre de liens créés")
REDIRECTS = Counter("shortener_redirects_total", "Nombre de redirections", ["result"])  # hit | miss
HTTP_REQUESTS = Counter("http_requests_total", "Requêtes HTTP", ["method", "route", "status"])
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Durée des requêtes HTTP",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par événement : facile à indexer (Loki, ELK, CloudWatch…)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("shortener")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False


def route_label(request: Request) -> str:
    """Gabarit de route (`/{code}`) et non le chemin réel : évite une explosion du nombre de séries."""
    route = request.scope.get("route")
    return getattr(route, "path", "non_routee")


async def observe_request(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration = time.perf_counter() - start
        route = route_label(request)
        HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
        HTTP_LATENCY.labels(request.method, route).observe(duration)
        logger.info(
            "requete",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                }
            },
        )
