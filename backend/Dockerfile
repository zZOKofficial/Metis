# METIS backend -- container image for Render (see render.yaml at the repo root).
#
# Build context is this directory (backend/), not the repo root:
#   docker build -t metis-backend backend/
#
# Kept separate from deployment/Dockerfile.backend, which belongs to the
# Cloud Run pipeline in deployment/cloudbuild.yaml.

FROM python:3.11-slim

# grpc, under google-cloud-firestore and firebase-admin, needs a CA bundle to
# open a TLS connection. Installed explicitly rather than assumed: the failure
# mode is a credentials error that looks like a wrong key, debugged remotely.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Run unprivileged. Nothing here needs root once the dependencies are installed.
RUN useradd --create-home --uid 1000 metis

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=metis:metis src/ ./src/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

USER metis

# Shell form so $PORT expands. Render assigns the port it expects the service to
# listen on (10000 by default) and requires binding 0.0.0.0; the fallback is for
# running the image locally. deployment/Dockerfile.backend hardcoded --port 8000
# while declaring an ENV PORT it never expanded, so nothing ever reached it.
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
