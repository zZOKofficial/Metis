# METIS — Status Report

**Date:** 2026-08-17 (updated 2026-09-04 — METIS 0.6.0)
**Auditor:** Automated codebase analysis
**Overall Completion:** ~88%

---

## 1. Executive Summary

METIS is a full-stack AI-powered business management platform built with Next.js (frontend), FastAPI (backend), Google Gemini AI, and Firestore. The project has a well-structured monorepo with clean separation of concerns. The core backend infrastructure (Milestones 0-4) and all frontend pages (Milestone 6) are complete. **All previously reported critical frontend-backend integration gaps are now resolved**: business setup persists to the backend, the business ID survives page reloads, the API base URL is environment-configurable, and every frontend page now calls the real API with loading and error states. **Chat conversations are persisted with multi-turn Gemini context and a history endpoint** — the Business Chat survives page reloads and the Manager Agent remembers prior turns. **METIS 0.3.0 (2026-08-12)** adds local **SQLite persistence** (`backend/data/metis.db` — data survives restarts without Google Cloud), **in-app Gemini API key management** in the Chat page, and fixes **approval execution failures** (staged approvals no longer fail on truncated/hallucinated IDs, and the Approval Center surfaces the real execution error instead of a generic message). **METIS 0.4.1 (2026-08-17)** turns the Business Chat into a catalog-management surface: the Operations Agent gained `create_product`/`delete_product` (staged into the Approval Center), Products gained an optional unique `product_key` (SKU) enforced by the API (409) and the agents, product PUT/DELETE now enforce existence and ownership (they previously wrote/deleted blindly), the Products UI was overhauled (live search, edit mode, delete with confirmation, product-key chips), and a frontend favicon set was added. **METIS 0.4.2** adds the `set_stock` inventory-override tool, which executes immediately — the owner can say "mark Deadpool's Golden Glock out of stock" and it happens on the spot instead of the agent reporting it can't. **METIS 0.4.3** makes the backend serve the favicon the browser requests (`/favicon.ico` + `/icon.svg` routes in `backend/src/main.py`, static copies under `backend/src/static/`, hidden from the `/docs` schema). **METIS 0.5.0 (2026-08-17, Phase 0 baseline sync)** reconciles the docs with the codebase: the **customer-facing storefront chat is already implemented** (public `frontend/src/app/storefront/[businessId]/page.tsx` + `GET/POST /api/storefront/{business_id}/history|chat`, commit `04645a0` 2026-08-12), so Milestone 7's step 2 is complete and the integration-gap table is corrected. Version marker bumped to 0.5.0 everywhere. **Phase 1 (E2E verification) done**: `backend/scripts/e2e_demo.py` (committed) passes **27/27** against a clean SQLite DB — REST CRUD, `product_key` 409, cross-business 404, server-side totals, inventory decrement, revenue booking, analytics, plus **live Gemini flows** (owner chat stages `create_product` → approve → catalog updated; storefront chat stages `create_order` → approve → stock 8→6). Supporting changes: `METIS_DB_PATH` env override for isolated test DBs. **Phase 1B started (demo experience)**: `POST /api/demo/seed` + Setup Wizard "Load the demo store" button (5 products, 3 customers, 3 revenue-bearing orders); Orders page now shows the customer name under the `customer #XXXX` tag; new **order memo PDF** (`/orders/{orderId}/receipt`, print-to-PDF, zero new deps). **METIS 0.6.0 (2026-09-04, Phase 1B second batch)** finishes most of the remaining demo-experience work: **mock AI mode** (`METIS_MOCK_AI=1`) answers common owner-chat intents deterministically with no Gemini key, by pattern-matching the message and dispatching to the same tool the real model would call; **SSE-streamed chat** for both the owner and storefront chat endpoints (`POST /api/chat/{business_id}/stream`, `POST /api/storefront/{business_id}/chat/stream`) — the reply is computed the normal way then replayed to the client word-by-word; and **photo→product drafting** (`POST /api/products/{business_id}/from-photo`) which asks Gemini vision for a JSON draft the owner reviews before saving. Remaining work is concentrated in Milestones 8-10 plus voice briefing (Phase 1B) and the 3B/5B hardening phases.

---

## 2. What Works

### Backend Infrastructure
| Component | Status | File |
|-----------|--------|------|
| FastAPI app with CORS, middleware, routers | ✅ Working | `backend/src/main.py` |
| Firestore service with local SQLite fallback (`backend/data/metis.db`, persistent) | ✅ Working | `backend/src/services/firestore.py` `SqliteDB` |
| Gemini AI service wrapper | ✅ Working | `backend/src/services/gemini.py` |
| Pydantic v2 data models (incl. chat schemas) | ✅ Working | `backend/src/models/schemas.py` |
| Environment configuration | ✅ Working | `backend/src/core/config.py` *(0.3.0: `APP_VERSION=0.3.0`; 0.4.1: `APP_VERSION=0.4.1` in config and `.env`; 0.4.3: `APP_VERSION=0.4.3`; 0.5.0: `APP_VERSION=0.5.0`; 0.6.0: `APP_VERSION=0.6.0`, adds `METIS_MOCK_AI`)* |
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
| Operations Agent (orders, inventory) | ✅ Working *(0.4.1: `create_product`, `delete_product` staged tools + `product_key_taken` check; 0.4.2: `set_stock` — immediate inventory override, 0 → out of stock)* | `backend/src/agents/operations.py` |
| Analytics Agent (metrics, insights) | ✅ Working | `backend/src/agents/analytics.py` |

### REST API Endpoints
| Endpoint | Status |
|----------|--------|
| `POST /api/business` | ✅ Implemented |
| `GET /api/business/{id}` | ✅ Implemented |
| `PUT /api/business/{id}` | ✅ Implemented |
| `GET/POST/PUT/DELETE /api/products/{business_id}` | ✅ Implemented *(0.4.1: optional `product_key` uniqueness → 409 on duplicate; PUT/DELETE verify existence + ownership (404) instead of blind writes)* |
| `GET/POST/PUT/DELETE /api/customers/{business_id}` | ✅ Implemented |
| `GET/POST/PUT/DELETE /api/orders/{business_id}` | ✅ Implemented |
| `GET /api/agents/{business_id}` | ✅ Implemented |
| `GET /api/chat/{business_id}/history` | ✅ Implemented (persisted, multi-turn) |
| `POST /api/chat/{business_id}` | ✅ Implemented (persists turns, returns full history) |
| `POST /api/chat/{business_id}/stream` | ✅ Implemented (SSE, word-chunked replay of the same computed response) *(0.6.0)* |
| `GET/POST /api/storefront/{business_id}/history` | ✅ Implemented (public, session-scoped) |
| `POST /api/storefront/{business_id}/chat` | ✅ Implemented (public — Sales Agent, `create_order` staged for approval, customer id server-verified) |
| `POST /api/storefront/{business_id}/chat/stream` | ✅ Implemented (public, SSE) *(0.6.0)* |
| `POST /api/products/{business_id}/from-photo` | ✅ Implemented (drafts a product from an uploaded photo via Gemini vision) *(0.6.0)* |
| `POST /api/demo/seed` | ✅ Implemented (creates seeded demo store — 5 products, 3 customers, 3 orders) |
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
| Business Chat | ✅ Implemented *(0.6.0: replies stream token-by-token over SSE)* | `frontend/src/app/chat/page.tsx` |
| Approval Center | ✅ Implemented *(0.3.0: approve/reject alerts show the real backend execution error)* | `frontend/src/app/approvals/page.tsx` |
| Activity Feed | ✅ Implemented | `frontend/src/app/activity/page.tsx` |
| Products | ✅ Implemented *(0.4.1: revamped — live search, edit mode, delete with confirm, product-key chips; 0.6.0: "▣ Scan a photo" drafts a product from an image)* | `frontend/src/app/products/page.tsx` |
| Orders | ✅ Implemented *(0.5.0: customer name shown under the `customer #XXXX` tag; per-order "⤓ Memo" → printable receipt PDF at `/orders/{orderId}/receipt`)* | `frontend/src/app/(owner)/orders/page.tsx`, `frontend/src/app/(owner)/orders/[orderId]/receipt/page.tsx` |
| Customers | ✅ Implemented | `frontend/src/app/customers/page.tsx` |
| Setup Wizard | ✅ Implemented *(0.5.0: "Load the demo store" button → `POST /api/demo/seed`)* | `frontend/src/components/SetupWizard.tsx` |
| Storefront Chat (public customer page — shopper check-in, catalog, staged orders) | ✅ Implemented *(0.6.0: replies stream token-by-token over SSE)* | `frontend/src/app/storefront/[businessId]/page.tsx` |
| Sidebar Navigation | ✅ Implemented *(0.3.0: `v0.3.0` in footer; 0.4.1: `v0.4.1`; 0.4.3: `v0.4.3`; 0.5.0: `v0.5.0`; 0.6.0: `v0.6.0`)* | `frontend/src/components/Sidebar.tsx` |
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

### New & Fixed Since 2026-08-12 (0.4.1 → 0.4.3)

| # | Release | Area | What | File |
|---|---------|------|------|------|
| 1 | 0.4.1 | Backend | Chat catalog tools: `create_product` (MEDIUM) and `delete_product` (HIGH) staged into the Approval Center, executed by the Operations Agent on approve | `backend/src/agents/operations.py`, `services/actions.py`, `api/routes.py` |
| 2 | 0.4.1 | Backend | `product_key` — optional SKU, unique per business; duplicate → 409; agents check it via `product_key_taken` | `backend/src/models/schemas.py`, `api/routes.py` |
| 3 | 0.4.1 | Backend | Product PUT/DELETE enforced existence + business ownership (previously wrote/deleted blindly) → 404 | `backend/src/api/routes.py` |
| 4 | 0.4.1 | Frontend | Products UI revamp: live search (name/category/key), edit mode, delete with confirmation, product-key chips; split into `ProductForm`/`ProductCard` | `frontend/src/app/(owner)/products/*` |
| 5 | 0.4.1 | Frontend | Favicon set (`icon.svg`, `favicon.ico`, `apple-icon.png`) — auto-served by Next.js | `frontend/src/app/` |
| 6 | 0.4.2 | Backend | `set_stock` — immediate inventory-override tool (no approval): "mark Deadpool's Golden Glock out of stock" zeroes stock instantly | `backend/src/agents/operations.py`, `services/actions.py` |
| 7 | 0.4.3 | Backend | Backend serves the favicon the browser requests: `GET /favicon.ico` (image/x-icon) + `GET /icon.svg` (image/svg+xml), static copies in `backend/src/static/`, routes hidden from the `/docs` schema; verified live (200s, `/api/*` untouched) | `backend/src/main.py`, `backend/src/static/` |
| 8 | 0.5.0 | Docs | Baseline sync: storefront customer chat (added 2026-08-12, commit `04645a0`) marked complete — endpoints, page, Milestone 7 → 95%, integration-gap table corrected | `docs/STATUS_REPORT.md`, `docs/MILESTONES.md` |
| 9 | 0.5.0 | Versioning | `APP_VERSION` bumped to 0.5.0 in `config.py`, `.env`, Sidebar footer, storefront footer, `package.json`/lock | `backend/src/core/config.py`, `backend/.env`, `frontend/src/components/Sidebar.tsx`, `frontend/src/app/storefront/[businessId]/page.tsx`, `frontend/package.json` |
| 10 | 0.5.0 | Testing | `backend/scripts/e2e_demo.py` — committed E2E suite: 27 checks incl. live Gemini staging/approval flows (verified green against clean SQLite DB) | `backend/scripts/e2e_demo.py` |
| 11 | 0.5.0 | Backend | `METIS_DB_PATH` env override for isolated SQLite DBs (tests/E2E) | `backend/src/core/config.py`, `services/firestore.py` |
| 12 | 0.5.0 | Demo | `POST /api/demo/seed` + Setup Wizard "Load the demo store" — seeds 5 products, 3 customers, 3 revenue orders (Deadpool's Den) | `backend/src/services/demo.py`, `api/routes.py`, `frontend/src/components/SetupWizard.tsx` |
| 13 | 0.5.0 | Frontend | Orders page shows customer name under the `customer #XXXX` tag | `frontend/src/app/(owner)/orders/page.tsx` |
| 14 | 0.5.0 | Frontend | Order memo PDF: `/orders/{orderId}/receipt` — printable docket (business, customer, items, totals, policies) via `@media print`, zero new dependencies | `frontend/src/app/(owner)/orders/[orderId]/receipt/page.tsx`, `globals.css` |
| 15 | 0.6.0 | Backend | Mock AI mode (`METIS_MOCK_AI=1`) — deterministic replies for common owner-chat intents (add/delete/restock/mark-out-of-stock a product, move an order to a status) with no Gemini key required | `backend/src/services/gemini.py` |
| 16 | 0.6.0 | Backend + Frontend | Streaming chat — owner and storefront chat stream over SSE (`POST /api/chat/{business_id}/stream`, `POST /api/storefront/{business_id}/chat/stream`); the reply is computed the normal way then replayed to the client word-by-word | `backend/src/api/routes.py`, `frontend/src/lib/sse.ts`, `frontend/src/lib/useStreamBatcher.ts` |
| 17 | 0.6.0 | Backend + Frontend | Photo→product — `POST /api/products/{business_id}/from-photo` drafts a product from an uploaded image via Gemini vision; Products page normalizes the photo client-side (capped 1024px, JPEG) before upload | `backend/src/api/routes.py`, `frontend/src/app/(owner)/products/page.tsx` |

### Integration Gaps

| Issue | Details |
|-------|---------|
| No real-time updates | Frontend has no WebSocket, SSE, or polling — requires manual refresh |
| No auth on any endpoint | All REST APIs are completely open to unauthenticated requests |

---

## 4. Missing Features (Per Milestones)

### Milestone 5 — Incomplete
- **Authentication context** — No login flow, no user sessions, no protected routes

### Milestone 7 — Partial (API layer verified 27/27; UI walkthrough pending)
- Core 12-step flow is wired: business setup, products, orders, approvals, chat, and activity all persist through the backend API
- **Chat flow (steps 8-9) upgraded**: conversation history persists, the Manager Agent gets the last 20 turns as multi-turn Gemini context, and the chat UI syncs with the server
- **Customer-facing storefront chat (step 2) implemented**: public `storefront/[businessId]` page (shopper check-in, catalog view, staging notice) + session-scoped `GET/POST /api/storefront/{business_id}/history|chat` backed by the Sales Agent with `STOREFRONT_TOOL_DECLARATIONS` (`search_products`, `recommend_products`, `check_inventory`, `create_order`); customer id server-verified on order staging *(commit `04645a0`, 2026-08-12; reconciled into docs 0.5.0)*
- **Approval execution fixed (0.3.0)**: staged approvals now execute even when Gemini references truncated/hallucinated IDs; failures show the real error
- **Scripted E2E verification committed (0.5.0)**: `backend/scripts/e2e_demo.py` — 27/27 green on a clean SQLite DB (CRUD, 409/404 guards, totals, inventory, revenue, analytics, approvals, owner chat `create_product` → approve, storefront chat `create_order` → approve → stock decrement)
- Remaining: single-click browser walkthrough of the 12-step scenario on the live UI (script covers the API layer end-to-end)
- Campaign creation flow partially exposed (via chat + Approval Center; no dedicated campaign UI)

### Milestone 8 — Not Started
- Firebase Auth integration
- Route protection middleware
- Role-based access control
- Input validation hardening
- API key protection

### Milestone 9 — Partial (verification only)
- `backend/tests/` directory is empty
- Zero committed unit/integration tests across components (pytest configured but unused)
- *(0.4.1-0.4.3: ad-hoc FastAPI `TestClient` suites exercised product CRUD (incl. the `product_key` 409 path), the staged `create_product`/`delete_product` approval flow, and `set_stock` — including the `KeyError` it crashed on before the fix; run locally, not yet committed)*
- *(0.5.0: `backend/scripts/e2e_demo.py` committed — 27/27 green, incl. live-Gemini approval flows; Phase 2 of the roadmap turns this into a permanent `backend/tests/` suite)*

### Milestone 10 — Partially Complete
- Cloud Build config fixed (image tags now valid); pipeline not yet run live
- Both Dockerfiles fixed 2026-08-12 (frontend `public/` COPY removed; `CMD` arrays) — ready for a real build
- Cloud Run service config not documented
- No environment variable setup guide for deployment

---

## 5. Recommended Next Steps

### Priority 1 — Critical Fixes
1. **Complete Phase 1B demo experience** — mock AI mode, streaming chat, photo→product (vision), voice briefing, 90-second demo script
2. **Browser walkthrough** — single-pass click-through of the 12-step scenario on the live UI (API layer already verified 27/27 by `scripts/e2e_demo.py`)

### Priority 2 — Testing Foundation
3. Write unit tests for agent routing and permission enforcement
4. Write integration tests for order creation and inventory updates (contract now accepts `{product_id, quantity}`; approval-failure path testable via `ApprovalStatus.FAILED`)
5. Add test fixtures with mock Firestore and Gemini

### Priority 3 — Security
6. Add Firebase Auth integration
7. Add route protection middleware
8. Add input sanitization on all endpoints

### Priority 4 — Deployment
9. Validate Cloud Build pipeline end-to-end (Dockerfiles now build: frontend `public/` COPY removed, `CMD` arrays fixed; tags use `$PROJECT_ID`/`$SHORT_SHA`)
10. Add environment variable documentation
11. Configure Cloud Run services

### Priority 5 — Production Readiness
12. Add WebSocket/SSE real-time updates (roadmap Phase 5)
13. Persist per-agent `AgentMemory` (short-term context/preferences) to Firestore — chat history persistence already done
14. Expose Marketing campaign creation flow in the UI
15. Commerce hardening: payment method/status on orders, price/discount/refund chat tools, VAT + delivery, cost price (profit), undo/rollback + approval diffs, notifications

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
| 7: E2E Demo Workflow | ✅ Verified | 95% |
| 8: Auth & Security | ❌ Not Started | 0% |
| 9: Testing | ❌ Not Started | 0% |
| 10: Deployment | ⚠️ Partial | 50% |

---

*Report generated via automated codebase analysis. Verify all findings against current codebase state.*
