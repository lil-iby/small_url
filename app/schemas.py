import re
from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

# Codes qui entreraient en collision avec les routes de l'application.
RESERVED_CODES = {"api", "healthz", "metrics", "docs", "redoc", "openapi.json"}
CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


class LinkCreate(BaseModel):
    url: AnyHttpUrl = Field(description="URL de destination (http ou https uniquement)")
    custom_code: str | None = Field(default=None, description="Code personnalisé facultatif")

    @field_validator("url")
    @classmethod
    def url_not_too_long(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if len(str(value)) > 2048:
            raise ValueError("URL trop longue (2048 caractères maximum)")
        return value

    @field_validator("custom_code")
    @classmethod
    def valid_custom_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not CODE_PATTERN.fullmatch(value):
            raise ValueError("Le code doit contenir 3 à 32 caractères : lettres, chiffres, - ou _")
        if value.lower() in RESERVED_CODES:
            raise ValueError("Ce code est réservé")
        return value


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    short_url: str
    target_url: str
    clicks: int
    created_at: datetime
