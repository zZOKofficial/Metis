# METIS — Development Milestones

> Build a company, not a science project.

**Last Updated:** 2026-08-11

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
- [x] Data models: Business, Product, Customer, Order, AgentLog, Approval — `backend/src/models/schemas.py`
- [x] Pydantic schemas for validation — `backend/src/models/schemas.py`
- [x] Environment configuration (.env) — `backend/src/core/config.py`
- [x] Health check endpoint — `backend/src/main.py` (`/health`)

## Milestone 2: Agent Framework ✅
**Goal:** Reusable agent infrastructure with structured communication

- [x] BaseAgent class with tools, permissions, memory — `backend/src/agents/base.py`
- [x] Agent communication protocol (structured JSON messages) — `backend/src/agents/base.py`
- [x] Permission system (who can talk to whom, who can do what) — `backend/src/agents/base.py` (`PERMISSION_MATRIX`)
- [x] Agent orchestrator (Manager delegates to specialists) — `backend/src/agents/manager.py`
- [x] Activity logging (all agent actions recorded) — `backend/src/agents/base.py` → `agent_log_service`
- [x] Error handling and fail-safes — `backend/src/services/firestore.py` (InMemoryDB fallback)

## Milestone 3: Specialized Agents ✅
**Goal:** All 6 agents functional with real tools

- [x] **Manager Agent** — orchestrates, delegates, summarizes — `backend/src/agents/manager.py`
- [x] **Sales Agent** — product search, recommendations, order creation — `backend/src/agents/sales.py`
- [x] **Support Agent** — FAQs, policy answers, escalation — `backend/src/agents/support.py`
- [x] **Marketing Agent** — campaign creation, content generation — `backend/src/agents/marketing.py`
- [x] **Operations Agent** — order management, inventory monitoring — `backend/src/agents/operations.py`
- [x] **Analytics Agent** — business metrics, insights, recommendations — `backend/src/agents/analytics.py`

## Milestone 4: API Layer ✅
**Goal:** Complete REST API for frontend consumption

- [x] `/api/business` — CRUD business profile
- [x] `/api/products` — CRUD products
- [x] `/api/customers` — CRUD customers
- [x] `/api/orders` — CRUD orders
- [x] `/api/agents` — agent status, activity, trigger actions
- [x] `/api/chat` — chat with Manager Agent
- [x] `/api/approvals` — list, approve, reject
- [x] `/api/analytics` — dashboard metrics

## Milestone 5: Frontend Foundation ⚠️
**Goal:** Next.js app with routing, layout, API client

- [x] Next.js 14 with App Router — `frontend/package.json`, `frontend/next.config.js`
- [x] Tailwind CSS configuration — `frontend/tailwind.config.js`
- [x] Shared layout with navigation — `frontend/src/app/layout.tsx`, `frontend/src/components/Sidebar.tsx`
- [x] API client (fetch wrapper) — `frontend/src/lib/api.ts` *(hardcoded to `http://localhost:8000/api`)*
- [x] TypeScript types matching backend models — `frontend/src/types/index.ts`
- [ ] Authentication context — **Not implemented**

## Milestone 6: Frontend Pages ✅
**Goal:** All key pages functional and polished

- [x] **Dashboard** — revenue, orders, customers, alerts, recommendations — `frontend/src/app/page.tsx`
- [x] **Agent Center** — agent status, tasks, success rates — `frontend/src/app/agents/page.tsx`
- [x] **Business Chat** — chat interface with Manager Agent — `frontend/src/app/chat/page.tsx`
- [x] **Approval Center** — pending actions with approve/reject — `frontend/src/app/approvals/page.tsx`
- [x] **Activity Feed** — chronological agent activity log — `frontend/src/app/activity/page.tsx`
- [x] **Products** — product management UI — `frontend/src/app/products/page.tsx`
- [x] **Orders** — order management UI — `frontend/src/app/orders/page.tsx`
- [x] **Customers** — customer management UI — `frontend/src/app/customers/page.tsx`

## Milestone 7: End-to-End Demo Workflow ❌
**Goal:** Complete scenario from the prompt working flawlessly

1. Owner adds a summer collection
2. Customer asks about a blue shirt under ৳2000
3. Sales Agent searches, checks inventory, recommends
4. Customer places an order
5. Operations Agent records the order
6. Inventory auto-updates
7. Analytics Agent detects demand
8. Manager Agent reports status
9. Owner asks for a promotion
10. Marketing Agent creates campaign
11. Owner approves
12. System records completed action

> **BLOCKED:** Frontend never persists business to backend. Business ID is generated locally (`'biz-' + Date.now()`) and stored only in `localStorage`. All API calls using these IDs will fail against the real backend. The `SetupWizard` component does not call `POST /api/business`.

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

- [x] Dockerfile for backend — `deployment/Dockerfile.backend`
- [x] Dockerfile for frontend — `deployment/Dockerfile.frontend`
- [ ] Cloud Run service configuration
- [ ] Cloud Build configuration — **Broken:** `deployment/cloudbuild.yaml` has typos (`metas` instead of `metis`, missing project ID in image tags)
- [ ] Environment variable setup
- [ ] Custom domain (optional)

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
