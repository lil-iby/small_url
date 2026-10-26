# --- Étape 1 : installation des dépendances dans un environnement virtuel ---
FROM python:3.13-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Étape 2 : image finale minimale, utilisateur non root ---
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
COPY --from=builder /opt/venv /opt/venv
# pip n'est pas utile à l'exécution : on le retire (et ses dépendances embarquées) pour réduire la surface d'attaque.
RUN rm -rf /opt/venv/lib/python3.13/site-packages/pip* /opt/venv/bin/pip* \
    /usr/local/lib/python3.13/site-packages/pip* /usr/local/bin/pip*
WORKDIR /srv
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
USER appuser
EXPOSE 8000
# Liveness : le processus répond (la disponibilité de la base est vérifiée par /readyz).
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"
# Les migrations sont appliquées au démarrage, puis uvicorn remplace le shell (exec) pour recevoir les signaux.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-server-header"]
