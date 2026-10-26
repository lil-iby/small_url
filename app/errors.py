"""Erreurs métier : indépendantes de FastAPI, donc réutilisables et testables seules."""


class ShortenerError(Exception):
    status_code = 400
    detail = "Erreur"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        self.detail = detail or self.detail


class LinkNotFoundError(ShortenerError):
    status_code = 404
    detail = "Lien introuvable"


class CodeTakenError(ShortenerError):
    status_code = 409
    detail = "Ce code est déjà utilisé"


class CodeGenerationError(ShortenerError):
    status_code = 503
    detail = "Impossible de générer un code unique"


class BlockedUrlError(ShortenerError):
    status_code = 422
    detail = "Cette destination n'est pas autorisée"
