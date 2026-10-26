# Fiche d'explication (pour l'entretien)

## Ce que fait le projet en une phrase
Un service web qui transforme une URL longue en lien court, avec des clics comptés, livré avec toute la chaîne qui permet de le tester, le sécuriser, le conteneuriser et (à venir) le déployer.

## Brique par brique

**1. L'application (`app/`)**
- `config.py` : lit les réglages dans les variables d'environnement (principe 12-factor : la même image tourne partout, seule la config change).
- `db.py` / `models.py` : accès à la base via SQLAlchemy. Un seul modèle : `Link` (code unique indexé, URL cible, compteur de clics).
- `schemas.py` : règles de validation (Pydantic). C'est ici que la sécurité des entrées est appliquée : on n'accepte que `http`/`https`, on interdit les codes réservés (`api`, `metrics`…).
- `main.py` : les routes. Le point à savoir expliquer : le compteur de clics s'incrémente côté base, de façon atomique.

*Questions probables :* « Pourquoi 302 et pas 301 ? » (cache navigateur) ; « Que se passe-t-il si deux codes générés sont identiques ? » (contrainte d'unicité, nouvelle tentative) ; « Comment évites-tu les redirections dangereuses ? » (validation du schéma d'URL).

**2. Sécurité (`security.py`, `SECURITY.md`)**
Clé API comparée en temps constant, limitation de débit (429 + `Retry-After`), en-têtes durcis (CSP, nosniff, DENY), domaines bloqués, démarrage refusé en production sans clé. *Question probable :* « Pourquoi `hmac.compare_digest` ? » (évite les attaques par mesure du temps de réponse).

**3. Tests (`tests/`)**
32 tests, couverture 99 % (seuil CI à 90 %) : cas nominaux, cas d'attaque, limiteur, migrations Alembic jouées sur une base vierge, et un test à 200 clics concurrents sur PostgreSQL réel (exécuté en CI).

**4. Base de données (`migrations/`)**
Alembic versionne le schéma ; le conteneur applique `alembic upgrade head` au démarrage. *Question :* « Et avec plusieurs réplicas ? » (job de migration séparé, voir ADR-4).

**5. Docker (`Dockerfile`, `docker-compose.yml`)**
Build multi-étapes, utilisateur non root, système de fichiers en lecture seule, `cap_drop: ALL`, `no-new-privileges`, `HEALTHCHECK`. Profil `monitoring` : Prometheus + Grafana préconfigurés.

**6. Observabilité (`observability.py`, `monitoring/`)**
Journaux JSON sans IP, `X-Request-ID`, métriques par route, 3 alertes (service down, taux d'erreur 5xx > 5 %, p95 > 500 ms), tableau de bord Grafana.

**7. CI/CD (`.github/workflows/`)**
Lint, tests avec PostgreSQL, Bandit, pip-audit, CodeQL, Trivy (image et configuration), test de bout en bout via compose, publication GHCR sur `main`, Dependabot. *Question :* « Que se passe-t-il si une dépendance a une faille ? » (pip-audit et Trivy font échouer le pipeline).

**8. Infrastructure en code (`infra/`)**
Terraform (serveur + pare-feu), Ansible (Docker, pare-feu UFW, secrets en 0600, Vault). Validé en CI mais pas appliqué sur un vrai serveur : à dire franchement en entretien.

## Ce que je sais expliquer et ce que je ne prétends pas
- Je prétends : concevoir, tester, sécuriser, conteneuriser, automatiser une chaîne complète pour un service.
- Je ne prétends pas : avoir opéré ce service en production réelle ni géré de la montée en charge.
