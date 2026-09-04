---
title: METIS Backend
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# METIS — backend

FastAPI service behind [METIS](https://github.com/zZOKofficial/Metis): six AI
agents that run a small business's catalog, orders, customers and analytics,
with every consequential action staged for the owner's approval.

The YAML above is a Hugging Face Space card. It is read when this directory is
pushed to a Space as a subtree, and ignored everywhere else.

## Running it

Nothing is required to start. With no configuration the service uses a local
SQLite file, leaves authentication off, and — with `METIS_MOCK_AI=true` —
answers agent chats deterministically without a Gemini key.

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000     # from backend/
pytest                                         # 137 tests, no network, no keys
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
| `GEMINI_API_KEY` | *(blank)* | Not needed when `METIS_MOCK_AI=true`. |
| `METIS_MOCK_AI` | `false` | Deterministic agent replies, no model calls. |
| `CORS_ORIGINS` | `localhost:3000,8000` | The frontend's origin. Accepts `a,b` or `["a","b"]`. |
| `DEBUG` | `true` | Turn off when hosted. |

## Deploying to a Space

```bash
docker build -t metis-backend .        # build context is this directory
docker run -p 7860:7860 metis-backend
curl localhost:7860/health
```

`/health` reports which database is actually serving (`firestore` or `sqlite`)
and whether authentication is being enforced — it resolves the real client
rather than echoing configuration, so a deployment that meant to reach
Firestore and quietly landed on an ephemeral SQLite file says so there, before
the restart that would have thrown the data away.

To publish, add the Space as a remote and push this directory as a subtree
from the repository root:

```bash
git remote add space https://huggingface.co/spaces/<user>/<space>
git subtree push --prefix=backend space main
```

Then set the variables above in the Space's settings, with the credentials and
the Gemini key as **secrets** rather than plain variables.
