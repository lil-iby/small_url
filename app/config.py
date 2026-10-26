from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Configuration lue depuis les variables d'environnement (principe 12-factor)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "production" impose une configuration de sécurité complète au démarrage.
    environment: str = "dev"
    database_url: str = "sqlite:///./dev.db"
    base_url: str = "http://localhost:8000"
    code_length: int = Field(default=7, ge=4, le=32)
    # Les tables sont créées automatiquement uniquement en dev/test : en production, Alembic.
    auto_create_tables: bool = False

    # Sécurité
    api_keys: str = ""  # clés d'API autorisées à créer des liens, séparées par des virgules
    blocked_domains: str = ""  # domaines interdits comme destination, séparés par des virgules
    rate_limit_create_per_minute: int = Field(default=30, ge=1)
    rate_limit_redirect_per_minute: int = Field(default=240, ge=1)
    trust_proxy_headers: bool = False  # True derrière un reverse proxy de confiance (X-Forwarded-For)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def api_key_list(self) -> list[str]:
        return _split(self.api_keys)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def blocked_domain_list(self) -> list[str]:
        return [domain.lower() for domain in _split(self.blocked_domains)]

    def check_production_requirements(self) -> None:
        """Refuse de démarrer en production sans les protections minimales."""
        if self.environment != "production":
            return
        problems = []
        if not self.api_key_list:
            problems.append("API_KEYS doit contenir au moins une clé en production")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL ne doit pas être SQLite en production")
        if problems:
            raise RuntimeError("Configuration de production invalide : " + " ; ".join(problems))


settings = Settings()
