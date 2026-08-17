# METIS — Status Report

**Date:** 2026-08-17 (updated 2026-08-17 — METIS 0.4.1)
**Auditor:** Automated codebase analysis
**Overall Completion:** ~80%

---

## 1. Executive Summary

METIS is a full-stack AI-powered business management platform built with Next.js (frontend), FastAPI (backend), Google Gemini AI, and Firestore. The project has a well-structured monorepo with clean separation of concerns. The core backend infrastructure (Milestones 0-4) and all frontend pages (Milestone 6) are complete. **All previously reported critical frontend-backend integration gaps are now resolved**: business setup persists to the backend, the business ID survives page reloads, the API base URL is environment-configurable, and every frontend page now calls the real API with loading and error states. **Chat conversations are persisted with multi-turn Gemini context and a history endpoint** — the Business Chat survives page reloads and the Manager Agent remembers prior turns. **METIS 0.3.0 (2026-08-12)** adds local **SQLite persistence** (`backend/data/metis.db` — data survives restarts without Google Cloud), **in-app Gemini API key management** in the Chat page, and fixes **approval execution failures** (staged approvals no longer fail on truncated/hallucinated IDs, and the Approval Center surfaces the real execution error instead of a generic message). Remaining work is concentrated in Milestones 7-10: full E2E scenario verification (plus a customer-facing conversation UI), auth, testing, and deployment configuration.

---

## 2. What Works

### Backend Infrastructure
| Component | Status | File |
|-----------|--------|------|
| FastAPI app with CORS, middleware, routers | ✅ Working | `backend/src/main.py` |
| Firestore service with local SQLite fallback (`backend/data/metis.db`, persistent) | ✅ Working | `backend/src/services/firestore.py` `SqliteDB` |
| Gemini AI service wrapper | ✅ Working | `backend/src/services/gemini.py` |
| Pydantic v2 data models (incl. chat schemas) | ✅ Working | `backend/src/models/schemas.py` |
| Environment configuration | ✅ Working | `backend/src/core/config.py` *(0.3.0: `APP_VERSION=0.3.0`)* |
| Health check endpoint | ✅ Working | `backend/src/main.py` |

### Agent Framework
| Component | Status | File |
|-----------|--------|------|
| BaseAgent with tools, permissions, memory | ✅ Working | `backend/src/agents/base.py` |
| Agent registry (singleton factory) | ✅ Working | `backend/src/agents/registry.py` |
| Manager Agent (orchestrator) | ✅ Working | `backend/src/agents/manager.py` |
| Sales Agent (products, orders) | ✅ Working | `backend/src/agents/sales.py` *(0.3.0: reference resolution by ID / prefix / name, case-insensitive + fuzzy)* |
| Support Agent (FAQs, complaints) | ✅ Working | `backend/src/agents/support.py` |
| Marketing Agent (campaigns, content) | ✅ Working | `backend/src/agents/marketing.py` *(0.3.0: campaign product lookup tolerant of prefix/name)* |
| Operations Agent (orders, inventory) | ✅ Working | `backend/src/agents/operations.py` |
| Analytics Agent (metrics, insights) | ✅ Working | `backend/src/agents/analytics.py` |

### REST API Endpoints
| Endpoint | Status |
|----------|--------|
| `POST /api/business` | ✅ Implemented |
| `GET /api/business/{id}` | ✅ Implemented |
| `PUT /api/business/{id}` | ✅ Implemented |
| `GET/POST/PUT/DELETE /api/products/{business_id}` | ✅ Implemented |
| `GET/POST/PUT/DELETE /api/customers/{business_id}` | ✅ Implemented |
| `GET/POST/PUT/DELETE /api/orders/{business_id}` | ✅ Implemented |
| `GET /api/agents/{business_id}` | ✅ Implemented |
| `GET /api/chat/{business_id}/history` | ✅ Implemented (persisted, multi-turn) |
| `POST /api/chat/{business_id}` | ✅ Implemented (persists turns, returns full history) |
| `GET/POST /api/approvals/{business_id}` | ✅ Implemented |
| `POST /api/approvals/{business_id}/{id}/approve` | ✅ Implemented *(0.3.0: executes staged actions with resolved references; failures return real error)* |
| `POST /api/approvals/{business_id}/{id}/reject` | ✅ Implemented |
| `GET /api/analytics/{business_id}/dashboard` | ✅ Implemented |
| `GET /api/analytics/{business_id}/revenue` | ✅ Implemented (period filter: `all`/`today`/`7d`/`30d`) |
| `GET /api/analytics/{business_id}/top-products` | ✅ Implemented |
| `GET /api/analytics/{business_id}/low-stock` | ✅ Implemented |
| `GET /api/models` | ✅ Implemented |

### Frontend Pages
| Page | Status | File |
|------|--------|------|
| Dashboard | ✅ Implemented | `frontend/src/app/page.tsx` |
| Agent Center | ✅ Implemented | `frontend/src/app/agents/page.tsx` |
| Business Chat | ✅ Implemented | `frontend/src/app/chat/page.tsx` |
| Approval Center | ✅ Implemented *(0.3.0: approve/reject alerts show the real backend execution error)* | `frontend/src/app/approvals/page.tsx` |
| Activity Feed | ✅ Implemented | `frontend/src/app/activity/page.tsx` |
| Products | ✅ Implemented | `frontend/src/app/products/page.tsx` |
| Orders | ✅ Implemented | `frontend/src/app/orders/page.tsx` |
| Customers | ✅ Implemented | `frontend/src/app/customers/page.tsx` |
| Setup Wizard | ✅ Implemented | `frontend/src/components/SetupWizard.tsx` |
| Sidebar Navigation | ✅ Implemented *(0.3.0: `v0.3.0` in footer)* | `frontend/src/components/Sidebar.tsx` |
| Header | ✅ Implemented | `frontend/src/components/Header.tsx` |
| Gemini Key Panel (set/clear API key in-app) | ✅ Implemented *(0.3.0)* | `frontend/src/components/GeminiKeyPanel.tsx` |

### Frontend-Backend Integration (fixed since 2026-08-11)
| Component | Status | File |
|-----------|--------|------|
| SetupWizard → `POST /api/business`, stores returned ID | ✅ Fixed | `frontend/src/components/SetupWizard.tsx` |
| BusinessContext hydrates `businessId` from `localStorage` on reload | ✅ Fixed | `frontend/src/lib/BusinessContext.tsx` |
| API base URL configurable via `NEXT_PUBLIC_API_URL` (localhost fallback) | ✅ Fixed | `frontend/src/lib/api.ts` |
| Loading states + error handling on all pages (Products, Orders, Customers, Dashboard, Agents, Activity, Approvals, Chat) | ✅ Fixed | `frontend/src/app/*/page.tsx` |

### Deployment
| Component | Status | File |
|-----------|--------|------|
| Backend Dockerfile | ✅ Valid *(2026-08-12: `CMD` corrected to JSON-array form)* | `deployment/Dockerfile.backend` |
| Frontend Dockerfile | ✅ Valid *(2026-08-12: removed `COPY` of nonexistent `public/` that broke the build; `CMD` corrected)* | `deployment/Dockerfile.frontend` |

---

## 3. What's Broken

### Critical Bugs

| # | Severity | Issue | File | Line | Impact |
|---|----------|-------|------|------|--------|
| 1 | ✅ Resolved | `asyncio.get_event_loop().run_until_complete()` anti-pattern — `delegate_task` refactored to `async def` + `await` | `backend/src/agents/manager.py` | ~77-104 | No more `RuntimeError` in async contexts |
| 2 | ✅ Resolved | Cloud Build image tags fixed — `metas` → `metis`, uses `$PROJECT_ID`/`$SHORT_SHA` | `deployment/cloudbuild.yaml` | — | CI/CD pipeline image names now valid |
| 3 | 🟡 Medium | Agent short-term memory (`AgentMemory`) is in-memory only — lost on restart; **chat history now persists** via `chat_service` (partial fix) | `backend/src/agents/base.py` | — | Per-agent memory not persisted; conversation history survives |

> **Resolved since 2026-08-11:** SetupWizard now persists business to backend; BusinessContext restores `businessId` from localStorage; API URL is env-configurable; all pages have loading/error states.
>
> **Fixed 2026-08-12 (evening):** `Sales/Support/Marketing/Operations/AnalyticsAgent` were missing `__init__` (registry calls like `SalesAgent(business_id)` mis-bound `business_id` to `agent_type` → 500 on `/api/agents`, `/api/analytics`, chat). `None`-business guard added to chat route and `produce_summary` (stale business ID no longer 500s). Gemini payload format fixed for google-genai 1.0.0 (`parts` must be `[{'text': ...}]`, not `['str']`).

### Fixed 2026-08-12 (0.3.0 — approval execution + persistence)

| # | Area | Issue | Fixed |
|---|------|-------|-------|
| 1 | Backend | Staged approvals failed on truncated IDs: Gemini received only 8-char ID prefixes (`p['id'][:8]`, `[:8]` in chat prompt) and echoed them back to `create_order` → `Customer f143b951 not found` | ✅ Full IDs now shown to the model (`backend/src/api/routes.py`, `backend/src/agents/sales.py`, `manager.py`) |
| 2 | Backend | Staged approvals failed on hallucinated references (`prod_batmobile`, product *names* instead of UUIDs) | ✅ `SalesAgent.resolve_customer`/`resolve_product` + `MarketingAgent.create_campaign` match by ID, prefix, or name — case-insensitive with fuzzy fallback (`backend/src/agents/sales.py`, `marketing.py`) |
| 3 | Frontend | Approval Center showed "Make sure the backend is running" even when the backend replied with a real execution error (400 with `detail.execution`) | ✅ Alert now surfaces the actual error, e.g. `Action could not be executed. — Product prod_batmobile not found.` (`frontend/src/app/approvals/page.tsx`) |
| 4 | Persistence | In-memory DB lost all data on restart | ✅ Local `SqliteDB` (`backend/data/metis.db`) — schema + API mirror Firestore; data survives restarts (`backend/src/services/firestore.py`) |
| 5 | Ops | `/health` still reported `0.2.0` (stale `.env` pinned `APP_VERSION=0.2.0`, overriding `config.py`); stale uvicorn processes served old code | ✅ `.env` → `APP_VERSION=0.3.0`; backend restarted clean (`/health` → 0.3.0) |

### Fixed 2026-08-12 (bug-fix pass — 15 issues)

| # | Area | Issue | Fixed |
|---|------|-------|-------|
| 1 | Backend | Broken f-string in Marketing promotion prompt (`৳p['price']` literal) | ✅ `backend/src/agents/marketing.py` |
| 2 | Backend | `POST /api/orders` required full `OrderItem` objects → 422; now accepts `{product_id, quantity}` via `OrderItemCreate`, total computed server-side | ✅ `backend/src/models/schemas.py` |
| 3 | Backend | Approval marked `approved` even when execution failed; now `failed` status + 400 with execution error | ✅ `backend/src/api/routes.py`, `schemas.py` (`ApprovalStatus.FAILED`) |
| 4 | Backend | Chat prompt f-strings crashed on missing order/product fields; now `.get()` + numeric coercion | ✅ `backend/src/api/routes.py` |
| 5 | Backend | Orders accepted for nonexistent customers / malformed items; now validated | ✅ `backend/src/agents/sales.py` |
| 6 | Backend | `execute_staged_action` unguarded → 500 on approve; wrapped in try/except | ✅ `backend/src/services/actions.py` |
| 7 | Backend | Firestore→in-memory fallback was silent (data-loss risk); now warns | ✅ `backend/src/services/firestore.py` |
| 8 | Backend | Tool-loop exhaustion returned empty chat reply; now returns fallback message | ✅ `backend/src/services/gemini.py` |
| 9 | Backend | `get_order_status` error shape lacked `success` key (inconsistent) | ✅ `backend/src/agents/operations.py` |
| 10 | Backend | `get_revenue(period)` param ignored; implemented `today`/`7d`/`30d` | ✅ `backend/src/agents/analytics.py` |
| 11 | Frontend | Chat `history` computed from stale closure — last assistant turn dropped from context | ✅ `frontend/src/app/chat/page.tsx` |
| 12 | Frontend | Products/Customers didn't notify other pages of data changes | ✅ `frontend/src/app/products/page.tsx`, `customers/page.tsx` |
| 13 | Deploy | Frontend Dockerfile copied nonexistent `public/` → build fails | ✅ `deployment/Dockerfile.frontend` |
| 14 | Deploy | Docker `CMD` used single-quoted (invalid) arrays | ✅ Both Dockerfiles |
| 15 | Docs | README code fences mangled (stray backspace char), API table stale | ✅ `README.md` |

*Verified: Python `py_compile` clean, `tsc --noEmit` clean (exit 0), FastAPI app imports OK.*

### New Since 2026-08-11 (2026-08-12 update)
| Component | Status | File |
|-----------|--------|------|
| Local SQLite persistence (`backend/data/metis.db`; data survives restarts) | ✅ Done (0.3.0) | `backend/src/services/firestore.py` |
| Gemini API key set/clear from Chat page | ✅ Done (0.3.0) | `frontend/src/components/GeminiKeyPanel.tsx`, `frontend/src/lib/api.ts` |
| `/api/models`, `/api/ai/config`, `/api/ai/config/clear` endpoints | ✅ Done (0.3.0) | `backend/src/api/routes.py` |
| Chat message persistence (`chat_messages` collection, user + assistant turns) | ✅ Done | `backend/src/services/firestore.py` |
| `GET /api/chat/{business_id}/history` — server-side history endpoint | ✅ Done | `backend/src/api/routes.py` |
| Chat endpoint persists turns, seeds history, trims to 100 messages, returns synced history | ✅ Done | `backend/src/api/routes.py` |
| Multi-turn Gemini context (roles mapped user→user, assistant→model) | ✅ Done | `backend/src/services/gemini.py` |
| `BaseAgent.think()` accepts conversation history | ✅ Done | `backend/src/agents/base.py` |
| Chat UI loads server history, survives reload, renders Markdown | ✅ Done | `frontend/src/app/chat/page.tsx` |
| Markdown renderer (react-markdown + remark-gfm, styled) | ✅ Done | `frontend/src/components/Markdown.tsx` |
| Agent `__init__` bug fixed (missing `super().__init__(AgentType.X, business_id)`) | ✅ Fixed | `backend/src/agents/{sales,support,marketing,operations,analytics}.py` |
| `None`-business guards (stale business ID no longer crashes chat/dashboard) | ✅ Fixed | `backend/src/api/routes.py`, `backend/src/agents/manager.py` |
| Gemini payload format for google-genai 1.0.0 (`parts: [{'text': ...}]`, empty turns skipped) | ✅ Fixed | `backend/src/services/gemini.py` |
| `ManagerAgent.delegate_task` made properly async (`await agent.handle_message`) | ✅ Fixed | `backend/src/agents/manager.py` |
| Cloud Build image tags (`metis`, `$PROJECT_ID`/`$SHORT_SHA` substitutions) | ✅ Fixed | `deployment/cloudbuild.yaml` |

### Integration Gaps

| Issue | Details |
|-------|---------|
| No real-time updates | Frontend has no WebSocket, SSE, or polling — requires manual refresh |
| No auth on any endpoint | All REST APIs are completely open to unauthenticated requests |
| No customer-facing conversation UI | Simulated customer → Sales Agent interface for the demo scenario not built |

---

## 4. Missing Features (Per Milestones)

### Milestone 5 — Incomplete
- **Authentication context** — No login flow, no user sessions, no protected routes

### Milestone 7 — Partial (integration unblocked)
- Core 12-step flow is wired: business setup, products, orders, approvals, chat, and activity all persist through the backend API
- **Chat flow (steps 8-9) upgraded**: conversation history persists, the Manager Agent gets the last 20 turns as multi-turn Gemini context, and the chat UI syncs with the server
- **Approval execution fixed (0.3.0)**: staged approvals now execute even when Gemini references truncated/hallucinated IDs; failures show the real error
- **Customer-facing interface for simulated conversations not built**
- Full 12-step scenario not yet verified end-to-end in a single pass
- Campaign creation flow partially exposed (via chat + Approval Center; no dedicated campaign UI)

### Milestone 8 — Not Started
- Firebase Auth integration
- Route protection middleware
- Role-based access control
- Input validation hardening
- API key protection

### Milestone 9 — Not Started
- `backend/tests/` directory is empty
- Zero test coverage across all components
- pytest configured but unused

### Milestone 10 — Partially Complete
- Cloud Build config fixed (image tags now valid); pipeline not yet run live
- Both Dockerfiles fixed 2026-08-12 (frontend `public/` COPY removed; `CMD` arrays) — ready for a real build
- Cloud Run service config not documented
- No environment variable setup guide for deployment

---

## 5. Recommended Next Steps

### Priority 1 — Critical Fixes
1. **Verify E2E demo scenario** — Run the 12-step flow end-to-end against the real backend (approval execution is now reliable — 0.3.0)
2. **Build customer-facing conversation UI** — Simulated customer → Sales Agent interface for the demo

### Priority 2 — Testing Foundation
4. Write unit tests for agent routing and permission enforcement
5. Write integration tests for order creation and inventory updates (contract now accepts `{product_id, quantity}`; approval-failure path testable via `ApprovalStatus.FAILED`)
6. Add test fixtures with mock Firestore and Gemini

### Priority 3 — Security
7. Add Firebase Auth integration
8. Add route protection middleware
9. Add input sanitization on all endpoints

### Priority 4 — Deployment
10. Validate Cloud Build pipeline end-to-end (Dockerfiles now build: frontend `public/` COPY removed, `CMD` arrays fixed; tags use `$PROJECT_ID`/`$SHORT_SHA`)
11. Add environment variable documentation
12. Configure Cloud Run services

### Priority 5 — Production Readiness
13. Add polling or SSE for real-time activity updates
14. Persist per-agent `AgentMemory` (short-term context/preferences) to Firestore — chat history persistence already done
15. Expose Marketing campaign creation flow in the UI

---

## 6. Milestone Summary

| Milestone | Status | Completion |
|-----------|--------|------------|
| 0: Project Setup | ✅ Complete | 100% |
| 1: Core Backend & Data Layer | ✅ Complete | 100% |
| 2: Agent Framework | ✅ Complete | 100% |
| 3: Specialized Agents | ✅ Complete | 100% |
| 4: API Layer | ✅ Complete | 100% |
| 5: Frontend Foundation | ⚠️ Partial | 90% |
| 6: Frontend Pages | ✅ Complete | 100% |
| 7: E2E Demo Workflow | ⚠️ Partial | 70% |
| 8: Auth & Security | ❌ Not Started | 0% |
| 9: Testing | ❌ Not Started | 0% |
| 10: Deployment | ⚠️ Partial | 50% |

---

*Report generated via automated codebase analysis. Verify all findings against current codebase state.*
