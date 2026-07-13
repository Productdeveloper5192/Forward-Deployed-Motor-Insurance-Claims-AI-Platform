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
claim's AI pipeline run can be replayed and audited after the fact.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, SQLite, PyJWT, bcrypt |
| AI pipeline | LangGraph, Anthropic Claude (or Azure Foundry) |
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
scripts/             seed_demo_data.py
storage/             SQLite DB file + uploaded claim documents
tests/               pytest suite
```

## Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)
- A Claude API key (Anthropic direct, or Azure Foundry) — only required to actually
  **submit** a claim; everything else (auth, claim drafts, policies, review, payout)
  works without it.

## Execution Commands

Run the backend and frontend in two separate terminals — both need to be up at the
same time. First-time setup only needs to happen once; after that, just the "run"
line in each block.

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

Without activating the venv, you can also call the interpreter directly (this is
what was used to verify the app in this session):

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend runs at **http://127.0.0.1:8000** — interactive API docs at `/docs`.

### Frontend — PowerShell / Git Bash (same commands either way)

```bash
cd Moto_insurance_claims/frontend
npm install          # first time only
npm run dev
```

Frontend runs at **http://localhost:5173** and talks to the backend via
`VITE_API_BASE_URL` (see `frontend/.env`, defaults to `http://127.0.0.1:8000`).

### Run the tests

```bash
cd Moto_insurance_claims
.venv/Scripts/python.exe -m pytest tests/ -v     # or: pytest tests/ -v, if the venv is activated
```

### Production build of the frontend

```bash
cd Moto_insurance_claims/frontend
npm run build        # type-checks + bundles to frontend/dist/
npm run preview       # serve that build locally to sanity-check it
```

### Stopping everything

Ctrl+C in each terminal running `uvicorn` / `npm run dev`. Neither process
daemonizes itself, so there's nothing to separately kill.

### Demo accounts

Seeded by `scripts/seed_demo_data.py`:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `admin123` |
| Adjuster | `adjuster@example.com` | `adjuster123` |
| Customer | `customer@example.com` | `customer123` |

Seeded policies: `POL-10001` (active, full coverage) and `POL-10002` (lapsed — use
this one to see the rules engine's hard-deny path).

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Signing secret for auth tokens — set a real value outside local dev |
| `ENVIRONMENT` | `development` / `production` label, surfaced on `/health` |
| `CLAUDE_PROVIDER` | `anthropic` or `foundry` |
| `ANTHROPIC_API_KEY` | Required if `CLAUDE_PROVIDER=anthropic` |
| `FOUNDRY_API_KEY` / `FOUNDRY_RESOURCE` | Required if `CLAUDE_PROVIDER=foundry` |
| `CLAUDE_MODEL` | Model id used for every pipeline node |

**Submitting a claim makes real, billed calls to whichever provider is configured.**
If the credentials don't match the selected provider, the workflow fails at whichever
node calls Claude first, and the claim is marked `failed` (visible in the audit log).

## Running the tests

```bash
pytest tests/ -v
```

28 tests: full rules-engine coverage (deny / cap / manual-review / auto-approve paths)
plus API integration tests for auth, claims, document upload, review decisions,
payout, notifications, and admin routes. The suite runs against an isolated in-memory
SQLite database and never calls the live Claude API or touches `storage/app.db`.

## API summary

| Router | Endpoints |
|---|---|
| `/auth` | register, login, me |
| `/claims` | create, list, get, upload document, submit, workflow status, pay |
| `/review` | queue (adjuster/admin), decision |
| `/admin` | policies (create/list), evaluation dashboard, audit log |
| `/notifications` | list, mark read |

Full interactive reference at `GET /docs` once the backend is running.

## Known limitations

These are deliberate MVP stand-ins, not oversights — each is a real infrastructure
decision that depends on where this gets deployed, not something a single pass can
resolve:

- **Background jobs** run in an in-process thread pool, not Celery/Redis — a process
  restart mid-workflow leaves that claim stuck in `processing`.
- **Policy RAG** is keyword-overlap search over one markdown file, not an embeddings
  / vector-store retrieval.
- **Notifications** are in-app only (polled by the frontend) — no email/SMS provider.
- **No Alembic** — schema changes are created via `create_all()` plus a small manual
  catch-up for new columns (see `app/db/database.py`), not a real migration tool.
- **No Docker/compose** — local Python venv + SQLite only.
