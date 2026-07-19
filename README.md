# Moto Insurance Claims

An end-to-end motor insurance claims platform: a FastAPI backend runs claims through
an 8-node LangGraph pipeline backed by Claude, a deterministic rules engine makes the
binding approve/deny/review decision, and a React SPA gives customers, adjusters, and
admins a UI over all of it.

**No claim is ever auto-approved or auto-denied purely on the AI's say-so.** The AI
pipeline produces an advisory recommendation with a rationale; a separate, auditable
rules engine (policy validity, coverage limits, fraud thresholds, cross-document
validation issues) makes the actual decision, and anything ambiguous goes to a human
adjuster.

## Contents

- [Architecture](#architecture)
- [Stack](#stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration-env)
- [Demo accounts and seed data](#demo-accounts-and-seed-data)
- [User roles and journeys](#user-roles-and-journeys)
- [API reference](#api-reference)
- [Security model](#security-model)
- [Testing](#testing)
- [Production readiness checklist](#production-readiness-checklist)
- [Troubleshooting](#troubleshooting)

## Architecture

```
Customer / Adjuster / Admin (React SPA, JWT auth)
            │
            ▼
   FastAPI  (/auth /claims /review /admin /notifications)
            │
   ┌────────┴─────────┐
   ▼                   ▼
SQLite (app.db)   Background worker (in-process thread pool)
+ local file           │
  storage              ▼
                LangGraph pipeline (per submitted claim)
                 1. document_extraction        — Claude, structured
                 2. policy_verification        — DB lookup, no LLM
                    ├─ policy invalid → skip to step 8
                 3. policy_rag                  — Claude + keyword retrieval over policy_handbook.md
                 4. cross_document_validation   — Claude, structured
                 5. vehicle_damage_analysis     — Claude, vision
                 6. fraud_risk_triage           — Claude, agentic tools + scoring
                 7. decision_support            — Claude, advisory recommendation
                 8. rules_engine                — deterministic, BINDING decision
```

Every node's input/output is persisted to `workflow_runs` / `node_executions`, so any
claim's AI pipeline run can be replayed and audited after the fact. `document_extraction`
runs before the policy lookup, so even a claim against an invalid or lapsed policy incurs
one Claude call before the rules engine hard-denies it — a deliberate ordering trade-off
(extraction data is captured regardless of outcome), not a bug, but worth knowing if you're
tracking API spend.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, SQLite, PyJWT, bcrypt |
| AI pipeline | LangGraph, Anthropic Claude (or Azure AI Foundry) |
| Background jobs | in-process `ThreadPoolExecutor` (MVP stand-in for Celery/Redis) |
| Frontend | React 19, Vite, TypeScript, React Router |
| Tests | pytest (rules engine unit tests + API integration tests) |

## Project structure

```
app/
  api/routes/       auth, claims, review, admin, notifications
  core/              config (env vars) and JWT/password security
  db/                SQLAlchemy engine/session + lightweight column migration
  models/            User, Policy, Claim, Document, WorkflowRun, NodeExecution, AuditLog, Notification
  rules_engine/      deterministic approve/deny/review logic (no LLM)
  schemas/           Pydantic request/response contracts
  services/          claims intake, file storage, audit log, notifications
  tools/             fraud-triage agent tools (policy lookup, claim history lookup)
  workers/           background task submission
  workflow/          LangGraph graph, per-node logic, Claude client, policy-handbook retrieval
  policy_data/       policy_handbook.md — the source the RAG node retrieves from
frontend/            React + Vite + TypeScript SPA (customer/adjuster/admin UI)
scripts/             seed_demo_data.py, generate_finetune_jsonl.py
storage/             SQLite DB file + uploaded claim documents
tests/               pytest suite
```

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)
- A Claude API key (Anthropic direct, or Azure Foundry) — only required to actually
  **submit** a claim; everything else (auth, claim drafts, policies, review, payout)
  works without it.

### Backend — PowerShell

```powershell
cd Moto_insurance_claims
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\seed_demo_data.py          # optional — creates demo users + policies
uvicorn app.main:app --reload --port 8000
```

### Backend — Git Bash / macOS / Linux

```bash
cd Moto_insurance_claims
python -m venv .venv
source .venv/Scripts/activate    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo_data.py   # optional — creates demo users + policies
uvicorn app.main:app --reload --port 8000
```

Without activating the venv, you can also call the interpreter directly:

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend runs at **http://127.0.0.1:8000** — interactive API docs at `/docs`.
Always run with `--reload` in development, or edits won't take effect until you
restart the process by hand.

### Frontend — PowerShell / Git Bash (same commands either way)

```bash
cd Moto_insurance_claims/frontend
npm install          # first time only
npm run dev
```

Frontend runs at **http://localhost:5173** and talks to the backend via
`VITE_API_BASE_URL` (see `frontend/.env`, defaults to `http://127.0.0.1:8000`).

### Production build of the frontend

```bash
cd Moto_insurance_claims/frontend
npm run build        # type-checks + bundles to frontend/dist/
npm run preview       # serve that build locally to sanity-check it
```

### Stopping everything

Ctrl+C in each terminal running `uvicorn` / `npm run dev`. Neither process
daemonizes itself, so there's nothing to separately kill.

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Signing secret for auth tokens — **must** be overridden outside local dev; the code default (`dev-secret-change-me`) is intentionally insecure |
| `ENVIRONMENT` | `development` / `production` label, surfaced on `/health` |
| `CLAUDE_PROVIDER` | `anthropic` or `foundry` |
| `ANTHROPIC_API_KEY` | Required if `CLAUDE_PROVIDER=anthropic` |
| `FOUNDRY_API_KEY` / `FOUNDRY_RESOURCE` | Required if `CLAUDE_PROVIDER=foundry` |
| `CLAUDE_MODEL` | Model id used for every pipeline node |

Other tunables live as code defaults in `app/core/config.py` rather than env vars —
`JWT_EXPIRE_MINUTES` (12h), and the rules-engine thresholds `AUTO_APPROVE_MAX_AMOUNT`
($3,000), `FRAUD_REVIEW_THRESHOLD` (60), `FRAUD_DENY_THRESHOLD` (85). Override them the
same way (they're read via `pydantic-settings`, so any of these also work as env vars).

**Submitting a claim makes real, billed calls to whichever provider is configured.**
If the credentials don't match the selected provider, the workflow fails at whichever
node calls Claude first, and the claim is marked `failed` (visible in the audit log).

## Demo accounts and seed data

Seeded by `scripts/seed_demo_data.py`:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `admin123` |
| Adjuster | `adjuster@example.com` | `adjuster123` |
| Customer | `customer@example.com` | `customer123` |

Seeded policies: `POL-10001` (active, full coverage) and `POL-10002` (lapsed — use
this one to exercise the rules engine's hard-deny path without needing a fraud/amount
edge case).

## User roles and journeys

- **Customer** — registers via `/auth/register` (always provisioned as `customer`,
  never a staff role), creates a claim draft against one of their policies, uploads
  supporting documents, submits it, and tracks status/notifications. Can only see
  their own claims (`403` on any claim they don't own).
- **Adjuster** — works the `/review/queue` (claims in `needs_review`), reads the AI
  recommendation and rationale alongside the deterministic rules-engine output, and
  submits a binding decision (`approved` + amount, or `denied`). Can mark an approved
  claim as `paid`.
- **Admin** — everything an adjuster can do, plus policy creation, staff user
  provisioning (`/admin/users` — the only way to create adjuster/admin accounts;
  self-registration can't escalate privilege), the audit log, and the evaluation
  dashboard (AI/rules-engine agreement rate, AI/human agreement rate, average fraud
  score).

## API reference

| Router | Endpoints |
|---|---|
| `/auth` | register, login, me |
| `/claims` | create, list, get, upload document, submit, workflow status, pay |
| `/review` | queue (adjuster/admin), decision |
| `/admin` | policies (create/list), staff users (create/list), evaluation dashboard, audit log |
| `/notifications` | list, mark read |

Full interactive reference at `GET /docs` once the backend is running.

## Security model

- **Auth** — stateless JWT (HS256), `Authorization: Bearer <token>`, 12h expiry by
  default. Passwords hashed with bcrypt.
- **RBAC** — enforced per-route via `require_roles(...)` dependency injection
  (`app/api/deps.py`); customer/adjuster/admin. Staff accounts can only be created by
  an existing admin — there's no self-service path to an elevated role.
- **Row-level access** — a customer can only read/act on their own claims
  (`_ensure_can_view` in `app/api/routes/claims.py`); verified to return `403` for
  cross-customer access.
- **Audit trail** — every state-changing action (claim created, document uploaded,
  claim submitted, workflow completed/failed, review decision, payout) is written to
  `audit_logs`, independent of the workflow-run/node-execution records the LangGraph
  pipeline produces.
- **Known gap** — `CORSMiddleware` currently allows `allow_origins=["*"]` with
  `allow_credentials=True`. This doesn't expose a practical vulnerability today (auth
  is a Bearer token in a header, not a cookie, so credentialed-CORS semantics don't
  apply), but it should be tightened to an explicit origin allowlist before any
  non-local deployment.
- **Validated fix** — adjuster approval now requires an explicit `approved_amount`;
  previously an approval submitted without one would pass validation and later crash
  `/claims/{id}/pay` (a `None` amount hit an f-string format spec), leaving the claim
  stuck as `paid` with no amount on record. Fixed in `app/api/routes/review.py` and
  enforced client-side in `ClaimDetailPage.tsx`.

## Testing

```bash
pytest tests/ -v
```

The suite (when present — see note below) covers full rules-engine logic (deny / cap /
manual-review / auto-approve paths) plus API integration tests for auth, claims,
document upload, review decisions, payout, notifications, and admin routes, run
against an isolated in-memory SQLite database. It never calls the live Claude API or
touches `storage/app.db`.

> **Current gap:** `tests/` is empty in this working tree — `conftest.py`,
> `test_api_claims.py`, and `test_rules_engine.py` have been deleted locally and not
> yet replaced. `pytest tests/ -v` has nothing to run until they're restored (`git
> checkout -- tests/` recovers the last-committed versions) or rewritten. Treat this as
> a blocker for calling the platform production-ready — see the checklist below.

## Production readiness checklist

This platform is architecturally sound for production (the advisory-AI /
binding-rules-engine split, the audit trail, the RBAC model), but several pieces are
deliberate MVP stand-ins that need to be swapped before a real deployment — each is an
infrastructure decision that depends on where this gets deployed, not an oversight:

| Area | Current state | Needed for production |
|---|---|---|
| Background jobs | In-process `ThreadPoolExecutor` | Celery/RQ + Redis (or equivalent) — a process restart mid-workflow currently strands that claim in `processing` forever |
| Database | SQLite file | Postgres (or similar) — SQLite's single-writer model won't hold up under concurrent adjusters/customers |
| Migrations | `create_all()` + a hand-written column patch in `app/db/database.py` | Alembic — the current approach doesn't handle drops, renames, or index changes |
| Policy retrieval | Keyword-overlap search over one markdown file | Real embeddings / vector-store retrieval, and a path to multiple policy documents |
| Notifications | In-app only, polled by the frontend | Email/SMS provider integration |
| Deployment | Local Python venv + SQLite, no containers | Docker/compose (or equivalent) + a process manager |
| Secrets | `.env` file, insecure default `JWT_SECRET` | A real secrets manager; enforce a non-default `JWT_SECRET` at startup |
| CORS | `allow_origins=["*"]` | Explicit allowlist of deployed frontend origin(s) |
| Test suite | Deleted in this working tree | Restore/rewrite before treating any change as verified |
| Observability | `logging.basicConfig` to stdout | Structured logging + error tracking (e.g. Sentry) for workflow failures, which currently only surface in the audit log and server logs |

## Troubleshooting

- **`uvicorn` starts but `/claims/{id}/submit` leaves the claim stuck in `processing`**
  — check the backend terminal for a traceback; the background worker logs unhandled
  exceptions (`app/workers/tasks.py`) but doesn't retry or surface them anywhere else
  yet. The claim's `workflow_runs` row will show `status=failed` with an `error` field
  once the exception propagates.
- **Claim submission fails immediately at `document_extraction`** — usually a
  provider/credential mismatch: check `CLAUDE_PROVIDER` in `.env` matches the API key
  variables you've actually set (`ANTHROPIC_API_KEY` vs `FOUNDRY_API_KEY` +
  `FOUNDRY_RESOURCE`).
- **Frontend can't reach the backend** — confirm `VITE_API_BASE_URL` in
  `frontend/.env` matches the backend's actual host/port, and that CORS
  (`allow_origins`) isn't blocking it if you've since tightened it per the checklist
  above.
- **New column added to a model but the app errors on it** — there's no Alembic;
  add a matching `ALTER TABLE` line to `_add_missing_columns()` in
  `app/db/database.py`, following the existing `paid_at` example, or delete
  `storage/app.db` in a throwaway dev environment to let `create_all()` rebuild it
  from scratch.
