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

**2. Les tests (`tests/`)**
9 tests automatiques qui vérifient les cas nominaux et les cas d'attaque (URL `javascript:`, codes réservés, doublons, 404). Ils utilisent une base SQLite en mémoire : rapides, sans dépendance.

**3. Docker (`Dockerfile`, `docker-compose.yml`)**
- Build en deux étapes : on installe les dépendances dans une première image, puis on ne copie dans l'image finale que le nécessaire (image plus petite, moins de surface d'attaque).
- Utilisateur non root : si l'application est compromise, l'attaquant n'a pas les droits root dans le conteneur.
- `HEALTHCHECK` : Docker sait si l'application répond.
- `docker-compose` : lance l'application et PostgreSQL ; l'application attend que la base soit prête (`depends_on` + `healthcheck`).

*Questions probables :* « Pourquoi un build multi-étapes ? » ; « Pourquoi ne pas mettre le mot de passe dans l'image ? » (variables d'environnement, secrets hors du code).

**4. À venir** : CI/CD (GitHub Actions), analyses de sécurité (CodeQL/Bandit, Trivy), Ansible, supervision (Prometheus/Grafana). Chaque brique aura sa fiche ici.
