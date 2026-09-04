# METIS backend -- container image for Hugging Face Spaces.
#
# Build context is this directory (backend/), not the repo root:
#   docker build -t metis-backend backend/
#
# Kept separate from deployment/Dockerfile.backend, which belongs to the
# Cloud Run pipeline in deployment/cloudbuild.yaml. A Space is its own git
# repository and builds the Dockerfile at its root, which is what backend/
# becomes when it is pushed there as a subtree.

FROM python:3.11-slim

# grpc, under google-cloud-firestore and firebase-admin, needs a CA bundle to
# open a TLS connection. Installed explicitly rather than assumed: the failure
# mode is a credentials error that looks like a wrong key, debugged remotely.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Spaces run containers unprivileged as uid 1000.
RUN useradd --create-home --uid 1000 metis

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=metis:metis src/ ./src/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PORT=7860

EXPOSE 7860

USER metis

# Shell form so $PORT is actually read. deployment/Dockerfile.backend hardcodes
# --port 8000 while declaring an ENV PORT it never expands, so a host that
# assigns a port is ignored and nothing ever reaches the app.
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
