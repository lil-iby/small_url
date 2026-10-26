# URL Shortener : projet DevSecOps

Un raccourcisseur d'URL volontairement simple, construit pour illustrer une chaîne DevSecOps complète :
conteneurs, intégration continue, analyses de sécurité, déploiement automatisé et supervision.

> État du projet : étape 1 (application + tests) et étape 2 (conteneurs) terminées.
> À venir : CI/CD GitHub Actions avec analyses de sécurité, Ansible, supervision Prometheus/Grafana.

## Fonctionnalités

| Route | Rôle |
|---|---|
| `POST /api/links` | Crée un lien court (code généré ou personnalisé) |
| `GET /{code}` | Redirige (302) vers l'URL d'origine et compte le clic |
| `GET /api/links/{code}` | Statistiques du lien (nombre de clics) |
| `GET /healthz` | Sonde de santé (vérifie aussi la base) |
| `GET /metrics` | Métriques Prometheus |

## Lancer le projet

En local, sans Docker (SQLite) :

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --reload
```

Avec Docker (application + PostgreSQL) :

```bash
docker compose up --build
curl -X POST localhost:8000/api/links -H 'content-type: application/json' -d '{"url":"https://example.com"}'
```

## Choix techniques

- **FastAPI + SQLAlchemy** : API typée, validation automatique des entrées, documentation OpenAPI sur `/docs`.
- **Sécurité des entrées** : seules les URL `http` et `https` sont acceptées (refus de `javascript:`, `file:`, etc.), codes réservés interdits, longueur limitée.
- **Codes aléatoires** avec le module `secrets` (non prévisibles), gestion des collisions par nouvelle tentative.
- **Compteur de clics atomique** (`UPDATE ... SET clicks = clicks + 1`) : pas de perte en cas d'accès concurrents.
- **Redirection 302** et non 301 : un 301 serait mis en cache par le navigateur et les clics ne seraient plus comptés.
- **Image Docker** en deux étapes, base `python:3.13-slim`, utilisateur non root, `HEALTHCHECK` intégré.
- **Configuration par variables d'environnement** (principe 12-factor) : aucun secret dans le code ni dans l'image.

## Limites connues (et pistes)

- Pas de migrations de base : les tables sont créées au démarrage. En production : Alembic.
- Pas de limitation de débit : en production, à placer devant (reverse proxy) ou via un middleware.
