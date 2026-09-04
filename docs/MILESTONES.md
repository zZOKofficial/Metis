# METIS — Development Milestones

> Build a company, not a science project.

**Last Updated:** 2026-09-04 (METIS 0.7.2)

---

## Milestone 0: Project Setup ✅
- Create monorepo structure (backend + frontend + docs + deployment)
- Define architecture and data models
- Set up development environment

## Milestone 1: Core Backend & Data Layer ✅
**Goal:** FastAPI app running with Firestore, basic CRUD for business entities

- [x] FastAPI application with CORS, middleware — `backend/src/main.py`
- [x] Firestore integration (google-cloud-firestore) with local SQLite fallback — `backend/src/services/firestore.py` *(2026-08-12 (0.3.0): InMemoryDB replaced with a persistent local `SqliteDB` (`backend/data/metis.db`) — all data now survives restarts without Google Cloud)*
- [x] Gemini/Vertex AI integration (google-genai) — `backend/src/services/gemini.py`
- [x] Data models: Business, Product, Customer, Order, AgentLog, Approval, ChatMessage — `backend/src/models/schemas.py` *(0.4.1: `Product` gained `product_key` — optional SKU-style identifier, unique per business; 0.7.1: `Business` gained `currency` (default `BDT`), a code from the curated list in `backend/src/core/currency.py`)*
- [x] Chat message persistence (`chat_messages` collection) — `backend/src/services/firestore.py` (`chat_service`)
- [x] Pydantic schemas for validation — `backend/src/models/schemas.py`
- [x] Environment configuration (.env) — `backend/src/core/config.py` *(0.3.0: `APP_VERSION` bumped to 0.3.0 in both config and `.env`; 0.4.1: bumped to 0.4.1, incl. the `.env` pin that overrides `config.py`; 0.4.3: bumped to 0.4.3; 0.5.0: bumped to 0.5.0; 0.6.0: bumped to 0.6.0, adds `METIS_MOCK_AI` flag)*
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
- [x] **Sales Agent** — product search, recommendations, order creation — `backend/src/agents/sales.py` *(2026-08-12 (0.3.0): `create_order` now resolves customer/product references by full ID, ID prefix, or name — case-insensitive, with fuzzy fallback — so staged approvals no longer fail on truncated or hallucinated IDs)*
- [x] **Support Agent** — FAQs, policy answers, escalation — `backend/src/agents/support.py`
- [x] **Marketing Agent** — campaign creation, content generation — `backend/src/agents/marketing.py` *(0.3.0: campaign product reference resolution likewise tolerant of prefix/name matches)*
- [x] **Operations Agent** — order management, inventory monitoring — `backend/src/agents/operations.py` *(0.4.1: added `create_product`, `delete_product` and `product_key_taken` uniqueness checks; 0.4.2: added `set_stock` — absolute inventory override, 0 → out of stock, executes immediately)*
- [x] **Analytics Agent** — business metrics, insights, recommendations — `backend/src/agents/analytics.py`

> **2026-08-12:** Fixed a regression where all agents except Manager were missing `__init__` (registry instantiation threw `TypeError`, 500s on `/api/agents`, `/api/analytics`). Each agent now defines `__init__(self, business_id)` calling `super().__init__(AgentType.X, business_id)`.
>
> **2026-08-12 (bug-fix pass):** Fixed a broken f-string in the Marketing Agent's promotion analysis prompt (`৳p['price']` rendered literally instead of the price) — `backend/src/agents/marketing.py`. Order creation now validates the customer exists and rejects malformed line items instead of 500ing — `backend/src/agents/sales.py`.

## Milestone 4: API Layer ✅
**Goal:** Complete REST API for frontend consumption

- [x] `/api/business` — CRUD business profile
- [x] `/api/products` — CRUD products *(0.4.1: optional `product_key` uniqueness enforced (409) on create/update; PUT/DELETE now verify product existence + business ownership instead of blind writes)*
- [x] `/api/customers` — CRUD customers
- [x] `/api/orders` — CRUD orders *(2026-08-12: `POST /api/orders/{business_id}` now accepts `{product_id, quantity}` line items via `OrderItemCreate` — previously required full `OrderItem` objects (422); `total_amount` is now computed server-side)*
- [x] `/api/agents` — agent status, activity, trigger actions
- [x] `/api/chat` — chat with Manager Agent (persists turns, returns synced history)
- [x] `/api/chat/{business_id}/history` — retrieve stored chat history
- [x] `/api/storefront/{business_id}/history` + `/api/storefront/{business_id}/chat` — public customer chat (session-scoped, Sales Agent, `create_order` staged for approval, customer id server-verified) *(added 2026-08-12, commit `04645a0`; documented in 0.5.0)*
- [x] `POST /api/demo/seed` — one-click demo store (5 products, 3 customers, 3 revenue-bearing orders) *(0.5.0)*
- [x] `POST /api/chat/{business_id}/stream` + `POST /api/storefront/{business_id}/chat/stream` — SSE variants of the owner and storefront chat endpoints; the reply is computed the normal way (agents, tool calls, persistence) then replayed to the client word-by-word as `delta` events, ending with a `done` event carrying the full response *(0.6.0)*
- [x] `POST /api/products/{business_id}/from-photo` — drafts a product (name, description, price, category) from an uploaded photo via Gemini vision; returns a best-effort JSON draft for the owner to review, not a saved product *(0.6.0)*
- [x] `/api/approvals` — list, approve, reject *(2026-08-12: failed executions now mark the approval `failed` (`ApprovalStatus.FAILED`) instead of `approved`, returning the execution error. **0.3.0:** the owner's approve/reject no longer 400s on truncated/hallucinated IDs — staged actions resolve references before executing; the chat prompt now shows full product/customer/order IDs so the model stops inventing them)*
- [x] `/api/analytics` — dashboard metrics
- [x] `GET /api/currencies` — curated currency list (code/symbol/name) for the Setup Wizard's picker *(0.7.1)*
- [x] `GET /api/agents/{business_id}/briefing` — Manager Agent's spoken-style business summary for the Dashboard's voice briefing button *(0.7.2)*

## Milestone 5: Frontend Foundation ⚠️
**Goal:** Next.js app with routing, layout, API client

- [x] Next.js 14 with App Router — `frontend/package.json`, `frontend/next.config.js`
- [x] Tailwind CSS configuration — `frontend/tailwind.config.js`
- [x] Shared layout with navigation — `frontend/src/app/layout.tsx`, `frontend/src/components/Sidebar.tsx` *(0.3.0: footer now shows `v0.3.0`; 0.4.1: shows `v0.4.1`; 0.4.3: shows `v0.4.3`; 0.5.0: shows `v0.5.0`; 0.6.0: shows `v0.6.0`)*
- [x] API client — `frontend/src/lib/api.ts` *(configurable via `NEXT_PUBLIC_API_URL`, falls back to `http://localhost:8000/api`; 0.3.0 adds `/models`, `/ai/config`, `/ai/config/clear` for the Gemini key panel)*
- [x] TypeScript types matching backend models — `frontend/src/types/index.ts`
- [ ] Authentication context — **Not implemented**

## Milestone 6: Frontend Pages ✅
**Goal:** All key pages functional and polished

- [x] **Dashboard** — revenue, orders, customers, alerts, recommendations — `frontend/src/app/page.tsx`
- [x] **Agent Center** — agent status, tasks, success rates — `frontend/src/app/agents/page.tsx`
- [x] **Business Chat** — chat interface with Manager Agent; persisted multi-turn history, Markdown rendering, survives reload; **Gemini API key can be set/cleared in-app** *(0.3.0)*; *(0.6.0: replies stream token-by-token over SSE via `frontend/src/lib/sse.ts` + `useStreamBatcher.ts`)* — `frontend/src/app/chat/page.tsx`, `frontend/src/components/GeminiKeyPanel.tsx`
- [x] **Approval Center** — pending actions with approve/reject; *error alerts now surface the real execution error from the backend (e.g. "Product X not found") instead of a generic message (0.3.0)* — `frontend/src/app/approvals/page.tsx`
- [x] **Activity Feed** — chronological agent activity log — `frontend/src/app/activity/page.tsx`
- [x] **Products** — product management UI — `frontend/src/app/products/page.tsx` *(0.4.1: revamped — live search (name/category/product key), edit mode reusing the ledger form, delete with confirmation, product-key chips; split into `ProductForm.tsx` / `ProductCard.tsx`; 0.6.0: "▣ Scan a photo" — client-side image normalize (capped to 1024px, JPEG) then `POST /products/{business_id}/from-photo` drafts the form)*
- [x] **Orders** — order management UI; customer name under the `customer #XXXX` tag; "⤓ Memo" → printable receipt PDF *(0.5.0)* — `frontend/src/app/(owner)/orders/page.tsx`, `frontend/src/app/(owner)/orders/[orderId]/receipt/page.tsx`
- [x] **Customers** — customer management UI — `frontend/src/app/customers/page.tsx`
- [x] **Storefront Chat** — public customer-facing page (shopper check-in, catalog view, Sales Assistant chat, staging notice) — `frontend/src/app/storefront/[businessId]/page.tsx` *(added 2026-08-12, commit `04645a0`; documented in 0.5.0; 0.6.0: replies stream token-by-token over SSE)*
- [x] **Setup Wizard demo shortcut** — "Load the demo store" seeds Deadpool's Den (5 products, 3 customers, 3 orders) via `POST /api/demo/seed` *(0.5.0)*

## Milestone 7: End-to-End Demo Workflow ✅ (95%)
**Goal:** Complete scenario from the prompt working flawlessly

1. [x] Owner adds a summer collection — `frontend/src/app/products/page.tsx` persists via `POST /api/products/{business_id}`
2. [x] Customer asks about a blue shirt under ৳2000 — **storefront chat implemented**: public `frontend/src/app/storefront/[businessId]/page.tsx` (shopper check-in, session-scoped history, catalog view) → `POST /api/storefront/{business_id}/chat` runs the Sales Agent with `STOREFRONT_TOOL_DECLARATIONS` (`search_products`, `recommend_products`, `check_inventory`, `create_order`); customer id server-verified, `create_order` staged into the Approval Center *(commit `04645a0` 2026-08-12; reconciled into docs 0.5.0)*
3. [x] Sales Agent searches, checks inventory, recommends — agent + `POST /api/orders` flow wired
4. [x] Customer places an order — `frontend/src/app/orders/page.tsx` + `POST /api/orders/{business_id}`
5. [x] Operations Agent records the order — `backend/src/agents/operations.py`
6. [x] Inventory auto-updates — `backend/src/agents/sales.py` (create_order)
7. [x] Analytics Agent detects demand — `backend/src/agents/analytics.py`
8. [x] Manager Agent reports status — `POST /api/chat/{business_id}` + `GET /api/chat/{business_id}/history` + `frontend/src/app/chat/page.tsx` *(multi-turn context: last 20 turns persisted to Firestore/SQLite)*
9. [x] Owner asks for a promotion — chat flow with persistent history
10. [~] Marketing Agent campaign flow — *agent works and campaigns are created via chat → owner approval, but no dedicated campaign UI/dashboard* (0.3.0: approvals referencing campaigns execute reliably)
11. [x] Owner approves — `frontend/src/app/approvals/page.tsx` + approve/reject endpoints *(0.3.0: approve no longer fails on truncated/hallucinated IDs; error alerts show the real reason)*
12. [x] System records completed action — agent logs + approval status updates

> **Previous blocker RESOLVED (2026-08-12):** `SetupWizard` now calls `POST /api/business` and stores the backend-returned ID; `BusinessContext` hydrates `businessId` from `localStorage` on reload. All pages (Products, Orders, Customers, Dashboard, Agents, Activity, Approvals, Chat) are wired to the backend API with loading/error states. **Update (2026-08-12):** Chat conversations are persisted server-side (`chat_messages` collection), the Manager Agent receives the last 20 turns as multi-turn Gemini context, and the chat UI loads history on mount and renders Markdown. **Update (2026-08-17, 0.5.0):** the customer-facing storefront chat (step 2) is implemented (commit `04645a0`) and the full scenario is **scripted-verified 27/27** (`backend/scripts/e2e_demo.py`); remaining: a single browser click-through of the live UI.
>
> **0.4.1 (2026-08-17):** The Business Chat gained real catalog management. `create_product` (MEDIUM) and `delete_product` (HIGH) are staged into the Approval Center — the owner approves and the Operations Agent executes. Products now carry an optional unique `product_key` (SKU) enforced by the API (409) and the agents; product PUT/DELETE routes previously wrote/deleted blindly — they now enforce existence and ownership. Products UI overhauled with live search, edit mode, delete with confirmation and product-key chips; frontend favicon set added (auto-served by Next.js). Version bumped to 0.4.1.
>
> **0.4.2 (2026-08-17):** Chat gained the `set_stock` inventory-override tool. It executes immediately instead of being staged — the owner can say "mark Deadpool's Golden Glock out of stock" and the stock is zeroed on the spot (`0` → out of stock) rather than the agent reporting it can't.
>
> **0.4.3 (2026-08-17):** The backend now serves the favicon the browser requests: `backend/src/static/favicon.ico` + `icon.svg` (copied from the frontend assets), served via new `GET /favicon.ico` (image/x-icon) and `GET /icon.svg` (image/svg+xml) routes in `backend/src/main.py`, hidden from the `/docs` schema. Verified on a live uvicorn: `/favicon.ico` → 200, `/icon.svg` → 200, `/health` → 200, `/api/*` untouched. Version bumped to 0.4.3 everywhere.
>
> **0.5.0 (2026-08-17, Phase 0 baseline sync):** Docs reconciled with the codebase — the customer-facing storefront chat (Milestone 7 step 2, `04645a0`) is marked complete, storefront endpoints/pages added to Milestones 4/6, Milestone 7 → 95%, integration-gap table corrected, and the version marker bumped to 0.5.0 everywhere (`config.py`, `.env`, Sidebar/storefront footers, `package.json`/lock).
>
> **0.5.0 (Phase 1 — E2E verification):** `backend/scripts/e2e_demo.py` committed — **27/27 checks green** on a clean SQLite DB: CRUD, `product_key` 409, cross-business 404, server-side totals, inventory decrement, revenue booking, analytics, approval 404 guard, plus live Gemini flows (owner chat stages `create_product` → approved → catalog updated; storefront chat stages `create_order` → approved → stock 8→6). Added `METIS_DB_PATH` env override for isolated test DBs.
>
> **0.5.0 (Phase 1B — demo experience, first batch):** `POST /api/demo/seed` + Setup Wizard "Load the demo store" button (5 products, 3 customers, 3 revenue orders). Orders page shows the customer name under the `customer #XXXX` tag. New **order memo PDF** — `/orders/{orderId}/receipt` renders the order as a printable docket (business, customer, items, totals, policies) via a new `@media print` block; "⤓ Memo" on every order card; zero new dependencies.
>
> **0.6.0 (Phase 1B — demo experience, second batch):** **Mock AI mode** (`METIS_MOCK_AI=1`) answers common owner-chat intents deterministically, no Gemini key required — pattern-matches the raw message for restock / mark out of stock / set stock / add product / delete product / move an order to a status, then dispatches straight to the same tool the real model would call (`backend/src/services/gemini.py::_mock_run_with_tools`). **Streaming chat** — owner and storefront chat now stream over SSE (`POST /api/chat/{business_id}/stream`, `POST /api/storefront/{business_id}/chat/stream`): the reply is computed the normal way (agents, tool calls, persistence, synced history) then replayed to the client word-by-word, consumed by `frontend/src/lib/sse.ts` (frame parsing) + `useStreamBatcher.ts` (throttled state updates) in both chat UIs. **Photo→product** — `POST /api/products/{business_id}/from-photo` asks Gemini vision for a JSON draft (name/description/price/category) from an uploaded photo; the Products page normalizes the photo client-side (canvas resize, capped to 1024px, JPEG) before upload, then opens the product form pre-filled with the draft for the owner to review. Remaining 1B: voice briefing.

> **0.3.0 (2026-08-12):** The chat prompt now shows full product/customer/order IDs (they were truncated to 8 chars, which led Gemini to stage approvals with invalid references); `create_order`/`create_campaign` resolve references by ID, prefix, or name (case-insensitive, fuzzy fallback for e.g. `prod_batmobile` → `Bat-Mobile`). Approval Center alerts surface the backend's actual execution error. Local persistence switched from in-memory to SQLite (`backend/data/metis.db`).

## Milestone 8: Auth & Security ❌
**Goal:** Production-ready security

- [ ] Firebase Authentication integration
- [ ] Route protection (middleware)
- [ ] Role-based access (owner vs agent)
- [ ] Input validation on all endpoints
- [ ] API key protection

> **NOT STARTED:** All API endpoints are completely open. No login page, no user management, no route protection.

## Milestone 9: Testing ✅ (committed suite)
**Goal:** Reliable, tested system

- [x] Agent routing tests — `backend/tests/test_agent_permissions.py`
- [x] Permission enforcement tests — `PERMISSION_MATRIX`/`can_request` fully covered, `backend/tests/test_agent_permissions.py`
- [x] Order creation flow tests — totals, inventory decrement, customer booking, insufficient-stock/unknown-customer/unknown-product rejection, `backend/tests/test_orders_api.py`
- [x] Inventory update tests — restock/set-stock/mark-out-of-stock via mock-AI chat, `backend/tests/test_chat_mock_ai.py`
- [x] Approval workflow tests — stage/approve/reject, already-resolved guard, cross-business 404, execution-failure → `FAILED` (not `approved`), `backend/tests/test_approvals_api.py`
- [x] API integration tests — business/products/customers/orders/analytics/demo-seed, `backend/tests/test_*_api.py`
- [x] Error handling tests — 404/409/400 paths across products, customers, orders, approvals

> **0.7.0 (2026-09-04):** Milestone 9 gets a committed pytest suite — `backend/tests/` (58 tests, `pytest.ini` at the backend root). `conftest.py` gives every test a fresh temp SQLite DB (each `FirestoreService` singleton's cached `_db` handle is reset alongside the module-level one) and mock AI mode on (`METIS_MOCK_AI=1`), so the whole suite runs with no Gemini key and never touches `backend/data/metis.db`. Covers business/product/customer/order CRUD, `product_key` 409, cross-business 404 ownership guards, order booking/release/reapply on status transitions, revenue recognition, the approval stage → approve/reject → execute pipeline (incl. the execution-failure → `FAILED` path), the full `PERMISSION_MATRIX`, mock-AI chat tool dispatch (restock/set-stock/mark-out-of-stock/add-product/delete-product/move-order-status), and demo seeding. Found and fixed a real bug along the way: `GET /analytics/{business_id}/revenue` silently ignored the documented `period` (`today`/`7d`/`30d`) query param — the route never accepted it, so it always behaved like `all`; `backend/src/api/routes.py` now passes it through. `backend/scripts/e2e_demo.py` (27/27, incl. live-Gemini flows) remains as-is for manual/live-key verification.

> **0.7.1 (2026-09-04):** Per-business currency selection. `Business.currency` (default `BDT`) is picked once in the Setup Wizard (step 1, alongside category) from a curated 18-currency list (`backend/src/core/currency.py`, served at `GET /api/currencies`); no FX conversion — a business only ever deals in its own currency. Replaced ~20 places across the backend that hardcoded the Taka symbol (`৳`) in agent prompts, chat summaries, and API routes with `BaseAgent.get_currency_symbol()` / `currency_symbol(business.get('currency'))`, and the frontend's shared `<Cash>` money component (`frontend/src/components/ui.tsx`) now takes an explicit `currency` prop resolved via `frontend/src/lib/currency.ts`, threaded through all 6 of its call sites plus the product-form price label. A business created before this field existed reads back as `BDT` — the pre-existing default — with no migration needed. Added `backend/tests/test_currency.py`.

> **0.7.2 (2026-09-04):** Voice briefing — the last planned Phase 1B item. `GET /api/agents/{business_id}/briefing` returns `ManagerAgent.produce_summary()`'s text; the Dashboard's new "🔊 Voice briefing" button (in the "From the manager's desk" panel) fetches it and reads it aloud with the browser's built-in `SpeechSynthesis` API — no server-side TTS, no new dependency, no API cost. `produce_summary()` now branches on `METIS_MOCK_AI`: in mock mode it builds the sentence directly from the already-computed metrics (revenue, order/customer/product counts, low-stock names) instead of calling Gemini, so the briefing reads real numbers even with no Gemini key configured — this matters because the feature is meant to work reliably in a live demo. Browser-verified end to end with Playwright (demo store → click briefing → correct numbers spoken, no console errors). Added `backend/tests/test_voice_briefing.py`.

## Milestone 10: Deployment ⚠️
**Goal:** Live on Google Cloud

- [x] Dockerfile for backend — `deployment/Dockerfile.backend` *(2026-08-12: `CMD` corrected to JSON-array form — single-quoted form previously relied on accidental shell fallback)*
- [x] Dockerfile for frontend — `deployment/Dockerfile.frontend` *(2026-08-12: removed `COPY --from=builder /app/public ./public` — no `public/` directory exists, which broke the image build; `CMD` corrected to JSON-array form)*
- [ ] Cloud Run service configuration
- [x] Cloud Build configuration — **Fixed 2026-08-12:** image tags corrected (`metis` instead of `metas`, `$PROJECT_ID`/`$SHORT_SHA` substitutions) — `deployment/cloudbuild.yaml`
- [ ] Environment variable setup
- [ ] Custom domain (optional)

> **2026-08-12 (bug-fix pass):** Full-sweep bug audit + fixes. Backend: broken Marketing f-string, `POST /orders` contract, failed-approval status, defensive chat prompt data, customer/line-item validation, `execute_staged_action` try/except, Firestore fallback warning, tool-loop exhaustion message, `get_order_status` shape, `get_revenue` period filtering. Frontend: chat history stale-closure fix, `notifyDataChanged()` on Products/Customers. Docs: README code fences + API table. Verified: Python compiles, `tsc --noEmit` clean, app imports OK.
>
> **0.3.0 (2026-08-12):** METIS 0.3.0 — SQLite local persistence (`backend/data/metis.db`, survives restarts), Gemini API key management in the Chat page (`GeminiKeyPanel`), and a fix for failing task approvals: approvals could not be executed when Gemini staged truncated or hallucinated product/customer IDs. Full IDs now appear in prompts; `create_order`/`create_campaign` resolve references by ID/prefix/name (case-insensitive + fuzzy). Approval Center errors now show the real backend reason. Backend restarted on the new code (`/health` returns 0.3.0).

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
- id, business_id, name, description, price, stock, product_key (optional, unique per business — SKU), category, variants, status, created_at

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
