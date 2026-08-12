# METIS — Development Milestones

> Build a company, not a science project.

**Last Updated:** 2026-08-12

---

## Milestone 0: Project Setup ✅
- Create monorepo structure (backend + frontend + docs + deployment)
- Define architecture and data models
- Set up development environment

## Milestone 1: Core Backend & Data Layer ✅
**Goal:** FastAPI app running with Firestore, basic CRUD for business entities

- [x] FastAPI application with CORS, middleware — `backend/src/main.py`
- [x] Firestore integration (google-cloud-firestore) — `backend/src/services/firestore.py`
- [x] Gemini/Vertex AI integration (google-genai) — `backend/src/services/gemini.py`
- [x] Data models: Business, Product, Customer, Order, AgentLog, Approval, ChatMessage — `backend/src/models/schemas.py`
- [x] Chat message persistence (`chat_messages` collection) — `backend/src/services/firestore.py` (`chat_service`)
- [x] Pydantic schemas for validation — `backend/src/models/schemas.py`
- [x] Environment configuration (.env) — `backend/src/core/config.py`
- [x] Health check endpoint — `backend/src/main.py` (`/health`)

## Milestone 2: Agent Framework ✅
**Goal:** Reusable agent infrastructure with structured communication

- [x] BaseAgent class with tools, permissions, memory — `backend/src/agents/base.py`
- [x] Agent communication protocol (structured JSON messages) — `backend/src/agents/base.py`
- [x] Permission system (who can talk to whom, who can do what) — `backend/src/agents/base.py` (`PERMISSION_MATRIX`)
- [x] Agent orchestrator (Manager delegates to specialists) — `backend/src/agents/manager.py` *(2026-08-12: `delegate_task` refactored to proper `async`/`await`)*
- [x] Activity logging (all agent actions recorded) — `backend/src/agents/base.py` → `agent_log_service`
- [x] Multi-turn conversation history for chat — `backend/src/services/gemini.py` (`_format_turn`), `BaseAgent.think(history=...)` *(2026-08-12: payload fixed for google-genai 1.0.0 — `parts` must be `[{'text': ...}]`)*
- [x] Error handling and fail-safes — `backend/src/services/firestore.py` (InMemoryDB fallback)

## Milestone 3: Specialized Agents ✅
**Goal:** All 6 agents functional with real tools

- [x] **Manager Agent** — orchestrates, delegates, summarizes — `backend/src/agents/manager.py`
- [x] **Sales Agent** — product search, recommendations, order creation — `backend/src/agents/sales.py`
- [x] **Support Agent** — FAQs, policy answers, escalation — `backend/src/agents/support.py`
- [x] **Marketing Agent** — campaign creation, content generation — `backend/src/agents/marketing.py`
- [x] **Operations Agent** — order management, inventory monitoring — `backend/src/agents/operations.py`
- [x] **Analytics Agent** — business metrics, insights, recommendations — `backend/src/agents/analytics.py`

> **2026-08-12:** Fixed a regression where all agents except Manager were missing `__init__` (registry instantiation threw `TypeError`, 500s on `/api/agents`, `/api/analytics`). Each agent now defines `__init__(self, business_id)` calling `super().__init__(AgentType.X, business_id)`.
>
> **2026-08-12 (bug-fix pass):** Fixed a broken f-string in the Marketing Agent's promotion analysis prompt (`৳p['price']` rendered literally instead of the price) — `backend/src/agents/marketing.py`. Order creation now validates the customer exists and rejects malformed line items instead of 500ing — `backend/src/agents/sales.py`.

## Milestone 4: API Layer ✅
**Goal:** Complete REST API for frontend consumption

- [x] `/api/business` — CRUD business profile
- [x] `/api/products` — CRUD products
- [x] `/api/customers` — CRUD customers
- [x] `/api/orders` — CRUD orders *(2026-08-12: `POST /api/orders/{business_id}` now accepts `{product_id, quantity}` line items via `OrderItemCreate` — previously required full `OrderItem` objects (422); `total_amount` is now computed server-side)*
- [x] `/api/agents` — agent status, activity, trigger actions
- [x] `/api/chat` — chat with Manager Agent (persists turns, returns synced history)
- [x] `/api/chat/{business_id}/history` — retrieve stored chat history
- [x] `/api/approvals` — list, approve, reject *(2026-08-12: failed executions now mark the approval `failed` (`ApprovalStatus.FAILED`) instead of `approved`, returning the execution error)*
- [x] `/api/analytics` — dashboard metrics

## Milestone 5: Frontend Foundation ⚠️
**Goal:** Next.js app with routing, layout, API client

- [x] Next.js 14 with App Router — `frontend/package.json`, `frontend/next.config.js`
- [x] Tailwind CSS configuration — `frontend/tailwind.config.js`
- [x] Shared layout with navigation — `frontend/src/app/layout.tsx`, `frontend/src/components/Sidebar.tsx`
- [x] API client — `frontend/src/lib/api.ts` *(configurable via `NEXT_PUBLIC_API_URL`, falls back to `http://localhost:8000/api`)*
- [x] TypeScript types matching backend models — `frontend/src/types/index.ts`
- [ ] Authentication context — **Not implemented**

## Milestone 6: Frontend Pages ✅
**Goal:** All key pages functional and polished

- [x] **Dashboard** — revenue, orders, customers, alerts, recommendations — `frontend/src/app/page.tsx`
- [x] **Agent Center** — agent status, tasks, success rates — `frontend/src/app/agents/page.tsx`
- [x] **Business Chat** — chat interface with Manager Agent; persisted multi-turn history, Markdown rendering, survives reload — `frontend/src/app/chat/page.tsx`
- [x] **Approval Center** — pending actions with approve/reject — `frontend/src/app/approvals/page.tsx`
- [x] **Activity Feed** — chronological agent activity log — `frontend/src/app/activity/page.tsx`
- [x] **Products** — product management UI — `frontend/src/app/products/page.tsx`
- [x] **Orders** — order management UI — `frontend/src/app/orders/page.tsx`
- [x] **Customers** — customer management UI — `frontend/src/app/customers/page.tsx`

## Milestone 7: End-to-End Demo Workflow ⚠️
**Goal:** Complete scenario from the prompt working flawlessly

1. [x] Owner adds a summer collection — `frontend/src/app/products/page.tsx` persists via `POST /api/products/{business_id}`
2. [ ] Customer asks about a blue shirt under ৳2000 — *customer-facing conversation interface not built*
3. [x] Sales Agent searches, checks inventory, recommends — agent + `POST /api/orders` flow wired
4. [x] Customer places an order — `frontend/src/app/orders/page.tsx` + `POST /api/orders/{business_id}`
5. [x] Operations Agent records the order — `backend/src/agents/operations.py`
6. [x] Inventory auto-updates — `backend/src/agents/sales.py` (create_order)
7. [x] Analytics Agent detects demand — `backend/src/agents/analytics.py`
8. [x] Manager Agent reports status — `POST /api/chat/{business_id}` + `GET /api/chat/{business_id}/history` + `frontend/src/app/chat/page.tsx` *(multi-turn context: last 20 turns persisted to Firestore)*
9. [x] Owner asks for a promotion — chat flow with persistent history
10. [ ] Marketing Agent campaign flow exposed in UI — agent exists, no UI to trigger campaign
11. [x] Owner approves — `frontend/src/app/approvals/page.tsx` + approve/reject endpoints
12. [x] System records completed action — agent logs + approval status updates

> **Previous blocker RESOLVED (2026-08-12):** `SetupWizard` now calls `POST /api/business` and stores the backend-returned ID; `BusinessContext` hydrates `businessId` from `localStorage` on reload. All pages (Products, Orders, Customers, Dashboard, Agents, Activity, Approvals, Chat) are wired to the backend API with loading/error states. **Update (2026-08-12):** Chat conversations are persisted server-side (`chat_messages` collection), the Manager Agent receives the last 20 turns as multi-turn Gemini context, and the chat UI loads history on mount and renders Markdown. Remaining: customer-facing simulated conversation UI and a full single-pass verification of the 12-step scenario.

## Milestone 8: Auth & Security ❌
**Goal:** Production-ready security

- [ ] Firebase Authentication integration
- [ ] Route protection (middleware)
- [ ] Role-based access (owner vs agent)
- [ ] Input validation on all endpoints
- [ ] API key protection

> **NOT STARTED:** All API endpoints are completely open. No login page, no user management, no route protection.

## Milestone 9: Testing ❌
**Goal:** Reliable, tested system

- [ ] Agent routing tests
- [ ] Permission enforcement tests
- [ ] Order creation flow tests
- [ ] Inventory update tests
- [ ] Approval workflow tests
- [ ] API integration tests
- [ ] Error handling tests

> **NOT STARTED:** `backend/tests/` directory exists but is empty. pytest and pytest-asyncio are in `requirements.txt` but zero tests written.

## Milestone 10: Deployment ⚠️
**Goal:** Live on Google Cloud

- [x] Dockerfile for backend — `deployment/Dockerfile.backend` *(2026-08-12: `CMD` corrected to JSON-array form — single-quoted form previously relied on accidental shell fallback)*
- [x] Dockerfile for frontend — `deployment/Dockerfile.frontend` *(2026-08-12: removed `COPY --from=builder /app/public ./public` — no `public/` directory exists, which broke the image build; `CMD` corrected to JSON-array form)*
- [ ] Cloud Run service configuration
- [x] Cloud Build configuration — **Fixed 2026-08-12:** image tags corrected (`metis` instead of `metas`, `$PROJECT_ID`/`$SHORT_SHA` substitutions) — `deployment/cloudbuild.yaml`
- [ ] Environment variable setup
- [ ] Custom domain (optional)

> **2026-08-12 (bug-fix pass):** Full-sweep bug audit + fixes. Backend: broken Marketing f-string, `POST /orders` contract, failed-approval status, defensive chat prompt data, customer/line-item validation, `execute_staged_action` try/except, Firestore fallback warning, tool-loop exhaustion message, `get_order_status` shape, `get_revenue` period filtering. Frontend: chat history stale-closure fix, `notifyDataChanged()` on Products/Customers. Docs: README code fences + API table. Verified: Python compiles, `tsc --noEmit` clean, app imports OK.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   NEXT.JS FRONTEND                   │
│  Dashboard | Agents | Chat | Approvals | Products    │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
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
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐  ┌─────────┐  ┌──────────┐
    │Firestore│  │  Gemini │  │Cloud Log │
    └─────────┘  └─────────┘  └──────────┘
```

## Data Models

### Business
- id, name, category, description, contact_email, phone, operating_hours, policies, goals, created_at

### Product
- id, business_id, name, description, price, stock, category, variants, status, created_at

### Customer
- id, business_id, name, email, phone, total_orders, total_spent, created_at

### Order
- id, business_id, customer_id, products (list), total_amount, status, created_at, updated_at

### AgentLog
- id, business_id, agent_type, action, details, status, created_at

### Approval
- id, business_id, agent_type, action, reason, risk_level, status, created_at, resolved_at

---

## Agent Communication Protocol

```json
{
  "requester": "manager",
  "target": "marketing",
  "task": "create_campaign",
  "context": {"product_id": "abc123", "goal": "increase_sales"},
  "priority": "normal",
  "requires_approval": true
}
```

## Permission Matrix

| Agent | Can Request | Can Access |
|-------|-------------|------------|
| Manager | All agents | All data |
| Sales | Operations | Products, Customers |
| Support | Manager | Products, Policies |
| Marketing | Analytics | Products, Analytics |
| Operations | Analytics | Orders, Inventory |
| Analytics | — | All data (read-only) |
