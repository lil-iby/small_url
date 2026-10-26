"""Briques de sécurité : authentification par clé d'API, limitation de débit, en-têtes HTTP."""

import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request
from starlette.responses import Response

from app.config import settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}


def apply_security_headers(response: Response) -> Response:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Protège la création de liens. Sans clé configurée (mode dev uniquement), l'accès est libre."""
    keys = settings.api_key_list
    if not keys:
        return
    provided = x_api_key or ""
    # compare_digest : comparaison en temps constant, pour ne pas révéler la clé par le temps de réponse.
    if not any(hmac.compare_digest(provided, key) for key in keys):
        raise HTTPException(status_code=401, detail="Clé d'API manquante ou invalide")


class RateLimiter:
    """Fenêtre glissante en mémoire, par client.

    Limite : l'état est local au processus. Avec plusieurs réplicas, il faut une limitation
    partagée (Redis) ou au niveau du reverse proxy.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_id(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "inconnu"


def limit_create(request: Request) -> None:
    if not limiter.allow(f"create:{client_id(request)}", settings.rate_limit_create_per_minute):
        raise HTTPException(status_code=429, detail="Trop de requêtes", headers={"Retry-After": "60"})


def limit_redirect(request: Request) -> None:
    if not limiter.allow(f"redirect:{client_id(request)}", settings.rate_limit_redirect_per_minute):
        raise HTTPException(status_code=429, detail="Trop de requêtes", headers={"Retry-After": "60"})
