"""Logique métier : aucune dépendance à FastAPI, uniquement SQLAlchemy et les erreurs métier."""

import secrets
import string
from urllib.parse import urlsplit

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import BlockedUrlError, CodeGenerationError, CodeTakenError, LinkNotFoundError
from app.models import Link

ALPHABET = string.ascii_letters + string.digits
MAX_GENERATION_ATTEMPTS = 5


def generate_code(length: int) -> str:
    """Code aléatoire cryptographiquement sûr (module `secrets`), donc non prévisible."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def check_destination(url: str, blocked_domains: list[str], own_host: str | None = None) -> None:
    """Refuse les domaines bloqués et les boucles (un lien court qui pointe vers le service lui-même)."""
    host = (urlsplit(url).hostname or "").lower()
    forbidden = list(blocked_domains)
    if own_host:
        forbidden.append(own_host.lower())
    for domain in forbidden:
        if host == domain or host.endswith("." + domain):
            raise BlockedUrlError


def create_link(
    db: Session,
    target_url: str,
    *,
    custom_code: str | None,
    code_length: int,
    blocked_domains: list[str],
    own_host: str | None = None,
) -> Link:
    check_destination(target_url, blocked_domains, own_host)

    if custom_code:
        link = Link(code=custom_code, target_url=target_url)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise CodeTakenError from None
        return link

    for _ in range(MAX_GENERATION_ATTEMPTS):
        link = Link(code=generate_code(code_length), target_url=target_url)
        db.add(link)
        try:
            db.commit()
            return link
        except IntegrityError:  # collision de code : on retente avec un autre code
            db.rollback()
    raise CodeGenerationError


def get_link(db: Session, code: str) -> Link:
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise LinkNotFoundError
    return link


def register_click(db: Session, code: str) -> str:
    """Incrémente le compteur côté base (atomique) et renvoie l'URL de destination."""
    link = get_link(db, code)
    db.execute(update(Link).where(Link.id == link.id).values(clicks=Link.clicks + 1))
    db.commit()
    return link.target_url
