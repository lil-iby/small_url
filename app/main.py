import secrets
import string
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app.models import Link
from app.schemas import LinkCreate, LinkOut

ALPHABET = string.ascii_letters + string.digits
MAX_GENERATION_ATTEMPTS = 5

LINKS_CREATED = Counter("shortener_links_created_total", "Nombre de liens créés")
REDIRECTS = Counter(
    "shortener_redirects_total", "Nombre de redirections", ["result"]  # hit | miss
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Création des tables au démarrage. En production, on utiliserait des migrations (Alembic).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="URL Shortener", version="1.0.0", lifespan=lifespan)


def generate_code(length: int) -> str:
    # secrets : générateur cryptographiquement sûr, pas de codes prévisibles.
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def to_out(link: Link) -> LinkOut:
    return LinkOut(
        code=link.code,
        short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
        target_url=link.target_url,
        clicks=link.clicks,
        created_at=link.created_at,
    )


@app.get("/healthz", tags=["ops"])
def healthz(db: Session = Depends(get_db)) -> dict[str, str]:
    """Sonde de santé : vérifie aussi que la base répond."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/links", response_model=LinkOut, status_code=201, tags=["links"])
def create_link(payload: LinkCreate, db: Session = Depends(get_db)) -> LinkOut:
    target = str(payload.url)

    if payload.custom_code:
        link = Link(code=payload.custom_code, target_url=target)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Ce code est déjà utilisé") from None
    else:
        for _ in range(MAX_GENERATION_ATTEMPTS):
            link = Link(code=generate_code(settings.code_length), target_url=target)
            db.add(link)
            try:
                db.commit()
                break
            except IntegrityError:  # collision de code : on retente
                db.rollback()
        else:
            raise HTTPException(status_code=503, detail="Impossible de générer un code unique")

    LINKS_CREATED.inc()
    return to_out(link)


@app.get("/api/links/{code}", response_model=LinkOut, tags=["links"])
def link_stats(code: str, db: Session = Depends(get_db)) -> LinkOut:
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Lien introuvable")
    return to_out(link)


@app.get("/{code}", tags=["redirect"])
def redirect(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        REDIRECTS.labels(result="miss").inc()
        raise HTTPException(status_code=404, detail="Lien introuvable")

    # Incrément atomique côté base : pas de perte de clics en cas d'accès concurrents.
    db.execute(update(Link).where(Link.id == link.id).values(clicks=Link.clicks + 1))
    db.commit()
    REDIRECTS.labels(result="hit").inc()
    # 302 (et non 301) : le navigateur ne met pas la redirection en cache, donc chaque clic est compté.
    return RedirectResponse(url=link.target_url, status_code=302)
