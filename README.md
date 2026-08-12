# METIS — Your Business. Operated by AI.

**METIS** (Μῆτις — Greek goddess of wisdom, practical intelligence, and cunning strategy) is an **AI-operated business management platform** for small businesses. It is not another chatbot that talks about your business — it is an **AI workforce** of specialized agents that perform real business tasks, collaborate with each other, use your real data and tools, and produce measurable business outcomes.

---

## Why METIS Exists

Small businesses run on the shoulders of one person. The owner handles customer support, sales conversations, marketing posts, order management, inventory tracking, and business analysis — usually on top of the actual work of running the business. Hiring dedicated employees for each of those roles is out of reach for a shop with a handful of daily orders; the result is missed messages, slow replies, lost sales, and decisions made on gut feeling instead of data.

Generic AI assistants don't solve this. They generate advice, but the advice still has to be executed by the owner, one task at a time. What a small business needs is not a consultant — it is **staff**. METIS provides that staff as an affordable, always-on AI workforce: six specialized agents that take responsibility for entire areas of the business, execute actions against real business data, and ask the owner only when a decision matters.

The core principle is simple:

> **Agents must perform actions, not merely generate text.**

A conversation is not an outcome. An order created, a stock level updated, a campaign drafted, a support question answered with the real policy — those are outcomes. METIS is built around that distinction.

---

## How METIS Works

The business owner stays the highest authority. Beneath them, a **Manager Agent** orchestrates a team of specialized agents, each with a defined responsibility, tools, permissions, memory, and audit logging:

| Agent | Role |
|-------|------|
| **Manager** | Orchestrates the workforce, delegates tasks, coordinates agents, requests owner approval, produces business summaries |
| **Sales** | Product inquiries, catalog search, recommendations, order creation |
| **Support** | Customer questions, policies, FAQs, complaints, escalation |
| **Marketing** | Campaign creation, promotional content, audience suggestions |
| **Operations** | Order lifecycle management, inventory tracking, low-stock alerts |
| **Analytics** | Business metrics, trends, insights, recommendations |

When the owner types a request into the Business Chat, the Manager Agent reasons over the current business state (revenue, orders, products, customers), then uses tools to act on it — reading real data, creating orders, staging campaigns — and reports back what was done or what is awaiting approval.

Inter-agent communication is structured and permission-controlled (e.g. Sales may request from Operations, Marketing may access Analytics, Analytics is read-only). Every action is logged to an auditable activity feed.

### Human Approval

The owner is always the final authority on money and reputation:

- **Low-risk actions** (analysis, reports, inventory warnings, drafts) execute automatically.
- **Medium/high-risk actions** (order creation, campaign publishing) are staged into the **Approval Center**, where the owner sees the action, the requesting agent, the reason, and the risk level — then approves or rejects. Only approved actions execute; failed executions are recorded as `failed`, never falsely reported as done.

---

## Why METIS Beats Traditional Approaches

| Approach | The reality |
|----------|-------------|
| **Hiring staff** | Expensive, slow to hire, limited hours, inconsistent quality |
| **Doing it manually** | The owner becomes the bottleneck; messages and orders slip through |
| **A generic chatbot** | Advice only — the owner still does every task itself |
| **One monolithic AI assistant** | No ownership of outcomes, no audit trail, no accountability |
| **METIS** | An always-on team with defined roles, permissions, real tool execution, auditable actions, and human approval at the decision points that matter |

METIS combines the affordability of software with the accountability of an employee: it doesn't tell you what to do — it does it, records it, and only stops to ask when the decision belongs to you.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   NEXT.JS FRONTEND                   │
│  Dashboard | Agents | Chat | Approvals | Products    │
│  Orders | Customers | Activity                       │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────▼──────────────────────────────┐
│                  FASTAPI BACKEND                      │
│  ┌─────────────────────────────────────────────┐    │
│  │            AGENT ORCHESTRATOR                │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │    │
│  │  │ Manager │ │  Sales  │ │ Support │       │    │
│  │  └────┬────┘ └────┬────┘ └────┬────┘       │    │
│  │       │           │           │             │    │
│  │  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐       │    │
│  │  │Marketing│ │Operations│ │Analytics│       │    │
│  │  └─────────┘ └─────────┘ └─────────┘       │    │
│  │  Permissions • Memory • Audit Log          │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐  ┌─────────┐  ┌──────────┐
    │Firestore│  │  Gemini │  │ Cloud Run│
    └─────────┘  └─────────┘  └──────────┘
```

- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI — modular monolith, one deployable service
- **AI:** Google Gemini (raw REST `generateContent` with a function-calling loop)
- **Database:** Cloud Firestore (with an in-memory fallback for local development without credentials)
- **Deployment:** Docker + Cloud Build + Cloud Run

```
backend/src/
├── main.py              # FastAPI app entry
├── core/config.py       # Environment configuration
├── models/schemas.py    # Pydantic v2 data models & enums
├── api/routes.py        # REST API layer
├── services/
│   ├── firestore.py     # Data access (Firestore + in-memory fallback)
│   ├── gemini.py        # Gemini client & tool-calling loop
│   └── actions.py       # Tool layer: read-only / direct / staged actions
└── agents/
    ├── base.py          # BaseAgent, permissions, memory, logging
    ├── registry.py      # Agent factory
    └── manager/sales/support/marketing/operations/analytics.py

frontend/src/
├── app/                 # Next.js pages (Dashboard, Chat, Approvals, ...)
├── components/          # AppShell, Sidebar, Header, SetupWizard, Markdown
├── lib/                 # API client, business context, refresh events
└── types/               # TypeScript models
```

---

## Getting Started

### Prerequisites

- Python 3.11, 3.12, or 3.13 (Python 3.14 not yet supported)
- Node.js 20+
- (Optional, for real persistence & AI) Google Cloud account with **Firestore** and a **Gemini API key**

> **No Google Cloud account?** The backend runs fully on a local SQLite database (`backend/data/metis.db`) so all data survives restarts, and the chat endpoint works if you supply a `GEMINI_API_KEY` (or save one from the Chat page). Without a key, the chat returns a "not configured" message — everything else works.

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your Google Cloud / Gemini credentials

uvicorn src.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`, health check at `/health`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. The Setup Wizard creates your business, and from there the full workflow is available: add products and customers, watch the agents work in the Activity Feed, chat with the Manager Agent, and handle approvals in the Approval Center.

The frontend talks to the backend via `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api`).

### Configuration (`backend/.env`)

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | Firestore project ID (empty → local SQLite DB) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to a service-account key |
| `GEMINI_API_KEY` | Gemini API key for the AI agents |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `DEBUG` | Enable debug behavior |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/business` | Create business |
| GET | `/api/business/{business_id}` | Get business |
| PUT | `/api/business/{business_id}` | Update business |
| POST | `/api/products/{business_id}` | Add product |
| GET | `/api/products/{business_id}` | List products |
| GET | `/api/products/{business_id}/{product_id}` | Get product |
| PUT/DELETE | `/api/products/{business_id}/{product_id}` | Update/delete product |
| POST | `/api/customers/{business_id}` | Add customer |
| GET | `/api/customers/{business_id}` | List customers |
| GET | `/api/customers/{business_id}/{customer_id}` | Get customer |
| POST | `/api/orders/{business_id}` | Create order |
| GET | `/api/orders/{business_id}` | List orders |
| GET | `/api/orders/{business_id}/{order_id}` | Get order |
| PUT | `/api/orders/{business_id}/{order_id}/status` | Update order status |
| GET | `/api/agents/{business_id}` | Agent status |
| GET | `/api/agents/{business_id}/activity` | Agent activity log |
| POST | `/api/chat/{business_id}` | Chat with Manager Agent |
| GET | `/api/chat/{business_id}/history` | Chat history |
| GET | `/api/approvals/{business_id}` | List approvals |
| POST | `/api/approvals/{business_id}/{approval_id}/approve` | Approve action |
| POST | `/api/approvals/{business_id}/{approval_id}/reject` | Reject action |
| GET | `/api/analytics/{business_id}/dashboard` | Dashboard metrics |
| GET | `/api/analytics/{business_id}/revenue` | Revenue (period: `all`/`today`/`7d`/`30d`) |
| GET | `/api/analytics/{business_id}/top-products` | Top products |
| GET | `/api/analytics/{business_id}/low-stock` | Low stock products |
| GET | `/api/models` | Available AI models |

---

## Deployment

Build and deploy with Google Cloud Build / Cloud Run:

```bash
# Build images
gcloud builds submit --config deployment/cloudbuild.yaml
```

The pipeline builds both images, pushes them to Container Registry, and deploys `metis-backend` and `metis-frontend` to Cloud Run (`us-central1`). Set the backend's `GEMINI_API_KEY` and Firestore credentials as Cloud Run environment variables, and point the frontend at the backend URL via `NEXT_PUBLIC_API_URL`.

---

## Roadmap

- **Done (Milestones 0-6):** core backend, agent framework, all 6 agents, REST API, all frontend pages
- **Partial (Milestones 7, 10):** E2E demo workflow, deployment config
- **Not started:** authentication & security, automated tests

See [`docs/MILESTONES.md`](docs/MILESTONES.md) for the detailed milestone breakdown and [`docs/STATUS_REPORT.md`](docs/STATUS_REPORT.md) for the latest status.

---

## License

MIT
