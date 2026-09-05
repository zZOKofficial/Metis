# METIS — backend

FastAPI service behind [METIS](https://github.com/zZOKofficial/Metis): six AI
agents that run a small business's catalog, orders, customers and analytics,
with every consequential action staged for the owner's approval.

## Running it

Nothing is required to start. With no configuration the service uses a local
SQLite file, leaves authentication off, and — with `METIS_MOCK_AI=true` —
answers agent chats deterministically without a Gemini key.

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000     # from backend/
pytest                                         # 160 tests, no network, no keys
```

## Configuration

Copy `.env.example` to `.env`. Every value is optional; the defaults are the
local-development ones.

| Variable | Default | Notes |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | *(blank)* | Set it and the service uses Firestore instead of SQLite. |
| `GOOGLE_APPLICATION_CREDENTIALS` | *(blank)* | Path to a service-account key file. |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | *(blank)* | The same key inlined, for hosts that can only inject secrets as environment variables. |
| `METIS_REQUIRE_FIRESTORE` | `false` | Refuse to fall back to SQLite. Turn on wherever the filesystem is ephemeral. |
| `METIS_AUTH_ENABLED` | `false` | Enforce business ownership. Turn on for anything reachable from the internet. |
| `FIREBASE_PROJECT_ID` | `GOOGLE_CLOUD_PROJECT` | Only needed if auth lives in a different project. |
| `GEMINI_API_KEY` | *(blank)* | The deployment's shared fallback key. Each owner can save their own in-app, which takes precedence. |
| `METIS_MOCK_AI` | `false` | Deterministic agent replies, no model calls. |
| `CORS_ORIGINS` | `localhost:3000,8000` | The frontend's origin. Accepts `a,b` or `["a","b"]`. |
| `DEBUG` | `true` | Turn off when hosted. |

## Container

```bash
docker build -t metis-backend .        # build context is this directory
docker run -p 8000:8000 metis-backend
curl localhost:8000/health
```

The image runs unprivileged and binds `$PORT` (falling back to 8000), which is
what lets a host assign its own port.

## Deploying

Hosting is declared in [`render.yaml`](../render.yaml) at the repo root —
Render builds this directory directly from GitHub, so there is nothing to push
separately. The two credentials and the frontend origin are entered in the
Render dashboard and never committed.

`/health` reports which database is actually serving (`firestore` or `sqlite`)
and whether authentication is being enforced — it resolves the real client
rather than echoing configuration, so a deployment that meant to reach
Firestore and quietly landed on an ephemeral SQLite file says so there, before
the restart that would have thrown the data away. It is also the blueprint's
`healthCheckPath`, which means a deploy with unusable credentials fails at the
gate instead of coming up broken.
