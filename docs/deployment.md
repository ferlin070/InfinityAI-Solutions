# Deployment Guide

> For lead devs setting up a real deployment. Written 2026-07-17, reflects the codebase as of the CrewAI/OpenAI AI execution layer landing (see [ai-execution-crewai.md](architecture/ai-execution-crewai.md)).

---

## 0. Architecture reality check — read this first

Today this is a **monolith**: the FastAPI backend serves the API *and* the frontend (static HTML/CSS/JS) as one process. `backend/src/api/routes.py` reads and returns `frontend/src/index.html` directly, and mounts `frontend/src/{css,js,icons}` as static file routes. The frontend is **not** a separate SPA build — it's plain HTML/CSS/JS with `fetch()` calls to relative paths like `/api/executions`, which only work because everything is same-origin today.

This has two consequences for this guide:

1. **The simple path (recommended right now):** deploy `backend/` as one service to Railway or Render. It serves the dashboard at the same URL as the API. No Vercel involved, works with zero code changes. See §3.
2. **The split path (backend on Railway/Render, frontend on Vercel):** requires three prerequisite code changes that are **not done yet** — see §4. Don't attempt the split until those land, or login and every API call will silently fail cross-origin.

There is also a stale, already-removed auto-deploy pipeline: `.github/workflows/sync_to_hf.yml` (Hugging Face Spaces auto-deploy) was deleted in commit `6c10c5a`. `README.md` still references it in places — treat this document as authoritative over that until README is fully cleaned up.

Also note: **`Dockerfile` at the repo root is deprecated** (pre-refactor leftover, points at a `main.py` that no longer matches the current module layout). Always point Railway/Render at **`backend/Dockerfile`**, with build context/root directory set to `backend/`.

---

## 1. Prerequisites

- GitHub repo access, `main` branch deployable at any commit (no CI gate currently enforces this — check `git log`/tests yourself before deploying)
- An OpenAI account with **billing enabled** at [platform.openai.com](https://platform.openai.com) — required for the AI execution layer (CrewAI + `OpenAIProvider`). **Known current blocker:** the key on file returns `insufficient_quota` (HTTP 429) — confirmed via a live test call during implementation. Add a payment method before expecting real executions to succeed, on any host.
- (Only if/when you reach proposal-v2.md's M0 milestone) A Supabase account — see §5. Not required for anything that exists in code today.

---

## 2. Environment variables reference

| Variable | Required? | Used by | Notes |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `backend/src/core/config.py` | `production` (default if unset) makes the app **refuse to start** without `ADMIN_EMAIL`/`ADMIN_PASSWORD` — this is an intentional fail-closed security check, not a bug. Use `development` for a quick fallback login (`bos@infinityai.com` / `password123`). |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Yes in production | same | Single hardcoded admin login — there is no per-user auth system yet. |
| `OPENAI_API_KEY` | Yes | `backend/src/ai/providers/openai_provider.py` | Get from platform.openai.com → API keys. Needs billing configured (see §1). |
| `CREWAI_TESTING` | Recommended: `true` | CrewAI itself | Suppresses CrewAI's one-time interactive "view your execution traces? [y/N]" stdin prompt. Without it, the first execution on a fresh container can stall briefly. Set this on every deploy target. |
| `NVIDIA_NIM_API_KEY` | No (legacy) | `backend/src/services/llm.py` | Only powers the **deprecated** `/api/execute` endpoint (`orchestrator.py`), kept only as a rollback path. Not needed for the current `/api/executions` endpoint. |
| `GAS_WEB_APP_URL`, `ZARA_DRIVE_FOLDER_ID`, `DANISH_DRIVE_FOLDER_ID`, `MAYA_DRIVE_FOLDER_ID`, `AMELIA_DRIVE_FOLDER_ID`, `AIMAN_DRIVE_FOLDER_ID`, `ADILA_DRIVE_FOLDER_ID`, `HAKIM_DRIVE_FOLDER_ID` | No (legacy) | `backend/src/services/drive.py` | Google Drive upload, used only by the deprecated orchestrator path. |
| `PORT` | No | `backend/src/main.py`, `backend/Dockerfile` | Defaults to `7860` (Hugging Face Spaces convention). Railway/Render inject their own — the Dockerfile now respects `$PORT` (fixed as part of this guide; previously hardcoded). |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Not yet read anywhere | — | Placeholder names for when proposal-v2.md's `db/` layer lands. See §5. |

Copy `.env.example` → `.env` locally and fill in real values. `.env` is gitignored — never put real secrets in `.env.example`.

---

## 3. Backend deployment (the simple, working-today path)

Pick **one** of Railway or Render — both work the same way (build from `backend/Dockerfile`).

### Option A: Railway

1. New Project → Deploy from GitHub repo → select this repo.
2. Settings → set **Root Directory** to `backend`.
3. Railway auto-detects `backend/Dockerfile`. If it offers a Nixpacks/buildpack option instead, force Dockerfile builds explicitly (Settings → Build → Builder → Dockerfile).
4. Variables tab → add every "Required" row from §2 (`ENVIRONMENT=production`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `OPENAI_API_KEY`, `CREWAI_TESTING=true`).
5. Railway injects `PORT` automatically — the fixed Dockerfile CMD now reads it, no action needed.
6. Deploy. Railway gives you a `*.up.railway.app` URL — the dashboard, login page, and `/api/executions` are all served from that one URL.
7. (Optional) Add a custom domain under Settings → Networking.

### Option B: Render

1. New → Web Service → connect this GitHub repo.
2. **Root Directory:** `backend`. **Environment:** Docker. Render will find `backend/Dockerfile` automatically given that root.
3. Environment tab → add the same "Required" variables as Railway above.
4. Render also injects `PORT` automatically and the app now respects it.
5. Deploy. Render gives you a `*.onrender.com` URL.
6. Free-tier note: Render's free web services spin down on idle and cold-start on the next request (10-60s) — fine for internal/demo use, not for anything latency-sensitive.

### Post-deploy checklist (either option)

- [ ] `GET /login` loads the login page
- [ ] Login with `ADMIN_EMAIL`/`ADMIN_PASSWORD` succeeds and sets a cookie
- [ ] Dashboard (`/`) loads with CSS/JS (confirms static file mounts work under the container's working directory)
- [ ] `POST /api/executions` with a real prompt returns `status: "success"` — this requires OpenAI billing to actually be resolved (see §1); until then expect `status: "error", message: "Ralat dalaman semasa berhubung dengan penyedia AI."`, which is the *correct* (not broken) behavior for an unbilled key

---

## 4. Frontend on Vercel (split deployment) — prerequisites not yet done

**Do not attempt this yet without doing the three fixes below first**, or login/API calls will silently fail from the deployed Vercel frontend (cookie won't be sent cross-origin, and the fetch calls will hit Vercel's own domain instead of the backend).

1. **CORS** (`backend/src/core/middleware.py`) currently allows `allow_origins=["*"]` with `allow_credentials=False` — the standard "public API, no cookies" config. Cross-origin cookie auth needs `allow_origins=["https://your-frontend.vercel.app"]` (a specific origin, not `*`) and `allow_credentials=True`.
2. **Session cookie `SameSite`** (`backend/src/api/routes.py`, `api_login`) is hardcoded `samesite="lax"`. Browsers won't send a `Lax` cookie on a cross-site `fetch()`. Cross-origin needs `samesite="none"` together with `secure=True` (already conditional on `ENVIRONMENT=production`, which is required for `SameSite=None` to be accepted by browsers anyway).
3. **Frontend API base URL** (`frontend/src/js/api.js`) currently calls relative paths (`fetch('/api/executions')`). Deployed separately on Vercel, that resolves against Vercel's own domain, not the backend. Needs a configurable base URL (e.g. a small `config.js` injected at Vercel build time via an environment variable, or a `<meta>` tag baked into `index.html` at deploy time) pointing at the Railway/Render URL from §3.

These three changes touch cross-origin security posture (broadening CSRF exposure surface) and should be a deliberate decision, not a silent side-effect of a deployment doc — flagging here rather than implementing. Ask if you want this done; it's a small, contained change once approved.

Once those land, Vercel setup itself is standard: New Project → import repo → **Root Directory:** `frontend/src` → Framework Preset: Other (static) → Build Command: none → Output Directory: `.` → deploy.

---

## 5. Supabase setup — preparatory only, nothing reads this yet

No code in this repo touches Supabase today. This section is prep for when [proposal-v2.md](architecture/proposal-v2.md)'s M0 milestone (multi-tenant schema, RLS, auth) actually begins — don't spend time on this for the current AI execution layer, which has zero DB dependency by design (see [ai-execution-crewai.md](architecture/ai-execution-crewai.md) §2-3, "no DB yet" was an explicit scoping decision).

When that work starts:

1. Create a project at [supabase.com](https://supabase.com) — pick a region close to your primary user base.
2. Settings → API gives you three values that will eventually map to env vars:
   - **Project URL** → `SUPABASE_URL`
   - **`anon` public key** → `SUPABASE_ANON_KEY` — safe for client-side use, RLS-scoped
   - **`service_role` key** → `SUPABASE_SERVICE_ROLE_KEY` — **server-side only** (API/worker processes), bypasses RLS entirely. Never send this to any frontend or log it. proposal-v2.md §3 already flags this explicitly.
3. Don't apply any schema yet — proposal-v2.md §3 (organizations, org_members, RLS policies, `agents`, `agent_runs`) and ai-execution-crewai.md §7 (`executions` table) define what's needed, and that migration work hasn't started.
4. When it does start, Supabase Auth (email/magic link) replaces the current single hardcoded `ADMIN_EMAIL`/`ADMIN_PASSWORD` login entirely — don't build anything assuming both auth systems coexist long-term.

---

## 6. Known issues / follow-ups

- **OpenAI `insufficient_quota`** — the current key has no billing configured. Confirmed via a real API call during implementation; not a code issue. Blocks real executions on every host until fixed.
- **`crewai` adds ~580MB** to the backend's dependency tree (chromadb bindings, onnxruntime, litellm, a full `kubernetes` client — none of which this app actually uses; CrewAI pulls them in regardless). Well within Railway/Render free-tier build limits, just makes builds slower and images bigger than the dependency list alone would suggest.
- **`docker-compose.yml`** is for local development only — Railway and Render build directly from `backend/Dockerfile` and ignore it.
- **`/api/execute` (legacy)** is still live, deprecated, kept only until the CrewAI replacement (`/api/executions`) has been in production a while. Don't wire new frontend code to it.
