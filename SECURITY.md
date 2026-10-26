# Politique de sécurité

## Signaler une vulnérabilité

Merci de ne pas ouvrir d'issue publique. Utilisez l'onglet **Security → Report a vulnerability** du dépôt GitHub
(signalement privé). Réponse visée sous 7 jours.

## Mesures en place

| Domaine | Mesure |
|---|---|
| Authentification | Clé API (`X-API-Key`) comparée en temps constant (`hmac.compare_digest`) ; le démarrage échoue en production sans clé |
| Abus | Limitation de débit par client (création et redirection), réponse 429 + `Retry-After` |
| Entrées | Validation Pydantic (URL http/https, 2048 caractères max, alias `[A-Za-z0-9_-]{3,32}`), codes réservés refusés |
| Anti-abus | Liste de domaines bloqués (sous-domaines inclus), refus des liens vers le service lui-même (boucles) |
| Injection | SQLAlchemy paramétré, aucune requête construite par concaténation |
| Aléa | Codes générés avec `secrets` (pas `random`) |
| En-têtes | CSP `default-src 'none'`, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy` |
| Journaux | JSON structuré, sans adresse IP ni paramètres de requête, identifiant de requête |
| Conteneur | Image multi-étapes, utilisateur non root, système de fichiers en lecture seule, `cap_drop: ALL`, `no-new-privileges` |
| Chaîne CI | Bandit, pip-audit, CodeQL, Trivy (image + configuration), Dependabot |
| Secrets | Aucun secret dans le dépôt ; `.env` ignoré ; Ansible Vault pour le déploiement |

## Limites connues (honnêtement)

- Le limiteur de débit est en mémoire : valable pour une instance. Plusieurs instances demanderaient Redis.
- Pas de gestion de comptes utilisateurs : une clé API partagée suffit pour ce périmètre.
- La redirection est en 302 : pas de vérification continue de la destination après création.
