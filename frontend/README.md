# Moto Insurance Claims — Frontend

React + Vite + TypeScript SPA for the [Moto Insurance Claims](../README.md) backend.
Role-based UI for Customer, Adjuster, and Admin, talking to the FastAPI API over
plain JWT-authenticated `fetch` calls.

## Run it

```bash
npm install
npm run dev
```

Requires the backend running separately (see the [root README](../README.md)).
Talks to it via `VITE_API_BASE_URL` in `.env` (defaults to `http://127.0.0.1:8000`).

## Structure

```
src/
  api/          typed client + request/response types for every backend route
  auth/         JWT-based auth context (login/register/logout, current user)
  components/   Layout (role-based nav), StatusBadge, WorkflowTimeline, Toaster
  pages/        one file per screen — customer, adjuster, and admin flows
  lib/          formatting helpers (currency, dates, title-casing statuses)
```

Routing (`src/App.tsx`) redirects each role to its home screen after login:
customers to `/claims`, adjusters to `/review`, admins to `/admin/policies`. A
shared `ClaimDetailPage` adapts its actions (upload/submit vs. decide vs. pay)
based on the logged-in user's role.

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | Start the Vite dev server with HMR |
| `npm run build` | Type-check (`tsc -b`) and produce a production build in `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run oxlint |
