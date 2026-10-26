import logging
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import services
from app.config import settings
from app.db import Base, engine, get_db
from app.errors import ShortenerError
from app.observability import (
    LINKS_CREATED,
    REDIRECTS,
    configure_logging,
    logger,
    observe_request,
)
from app.schemas import LinkCreate, LinkOut
from app.security import (
    apply_security_headers,
    limit_create,
    limit_redirect,
    require_api_key,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    settings.check_production_requirements()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if not settings.api_key_list:
        logger.warning("Aucune clé d'API configurée : la création de liens est ouverte (mode dev uniquement)")
    logger.info("demarrage", extra={"fields": {"environment": settings.environment}})
    yield


app = FastAPI(title="URL Shortener", version="2.0.0", lifespan=lifespan)
app.middleware("http")(observe_request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    return apply_security_headers(await call_next(request))


@app.exception_handler(ShortenerError)
async def shortener_error_handler(_: Request, exc: ShortenerError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def to_out(link) -> LinkOut:
    return LinkOut(
        code=link.code,
        short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
        target_url=link.target_url,
        clicks=link.clicks,
        created_at=link.created_at,
    )


@app.get("/healthz", tags=["ops"])
def healthz() -> dict[str, str]:
    """Liveness : le processus répond. Ne touche pas la base (sinon un incident base redémarre l'appli)."""
    return {"status": "ok"}


@app.get("/readyz", tags=["ops"])
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness : l'application peut servir du trafic (la base répond)."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/api/links",
    response_model=LinkOut,
    status_code=201,
    tags=["links"],
    dependencies=[Depends(require_api_key), Depends(limit_create)],
)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)) -> LinkOut:
    link = services.create_link(
        db,
        str(payload.url),
        custom_code=payload.custom_code,
        code_length=settings.code_length,
        blocked_domains=settings.blocked_domain_list,
        own_host=urlsplit(settings.base_url).hostname,
    )
    LINKS_CREATED.inc()
    logging.getLogger("shortener").info("lien_cree", extra={"fields": {"code": link.code}})
    return to_out(link)


@app.get("/api/links/{code}", response_model=LinkOut, tags=["links"])
def link_stats(code: str, db: Session = Depends(get_db)) -> LinkOut:
    return to_out(services.get_link(db, code))


@app.get("/{code}", tags=["redirect"], dependencies=[Depends(limit_redirect)])
def redirect(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    try:
        target = services.register_click(db, code)
    except ShortenerError:
        REDIRECTS.labels(result="miss").inc()
        raise
    REDIRECTS.labels(result="hit").inc()
    # 302 (et non 301) : le navigateur ne met pas la redirection en cache, donc chaque clic est compté.
    return RedirectResponse(url=target, status_code=302)
