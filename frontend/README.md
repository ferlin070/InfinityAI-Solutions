# frontend/ — build output (not source)

> **Stale-doc notice (2026-07-19):** this file used to describe a
> hand-authored vanilla HTML/CSS/JS dashboard living in `frontend/src/`
> (`css/`, `js/` folders, IBM Plex "dokumen pejabat" theme). That was
> replaced by a React + Vite dashboard back in commit `154ab70` ("migrate
> and upgrade frontend to modern dark-themed React + Vite dashboard"), but
> this file was never updated to match — if you were confused why
> `frontend/src/css` and `frontend/src/js` don't exist, that's why.

## Where the real source is

**`../frontend-react/src/`** — a React 19 + Vite + Tailwind app. That's
where you edit the dashboard, including the Agent Workspace UI
(`frontend-react/src/components/workspace/`).

## What `frontend/src/` actually is

`frontend/src/` is **generated build output** — `frontend-react/vite.config.js`
sets `build.outDir` to `../frontend/src` with `emptyOutDir: true`, so every
`npm run build` in `frontend-react/` wipes and regenerates this directory
(minified `assets/*.js`/`*.css`, a generated `index.html`, plus static
files copied from `frontend-react/public/`).

It is **gitignored** (see root `.gitignore`) — it used to be committed
directly, which turned every rebuild into an unreviewable diff of minified
JS. Don't hand-edit anything under `frontend/src/`; it will be silently
overwritten by the next build.

The backend (`backend/src/core/config.py`'s `get_frontend_dir()`) serves
whatever is on disk at `frontend/src/` directly — it doesn't know or care
whether that came from a build or was hand-placed there.

## Building it

```bash
cd frontend-react
npm ci
npm run build       # writes into ../frontend/src
```

For local (non-Docker) backend dev, run the build once before
`python -m src.main` — otherwise `frontend/src/` won't exist and the
dashboard route will fail to find `index.html`. For `docker-compose`, the
`backend`/`worker` services bind-mount `./frontend:/app/frontend` at
*runtime*, so a host-side build (as above) is enough; no in-container step
needed for local dev.

## Production builds

The root `../Dockerfile` (used by Railway, and by Render if you point Root
Directory at the repo root) builds `frontend-react/` in a Node stage and
copies the output into the final image — see that file. `../backend/Dockerfile`
does **not** build or bundle a frontend at all (its build context is
`backend/` only, which can't reach `frontend-react/` outside it); it's an
API-only image. See `../docs/deployment.md` for which Dockerfile to point
which platform at.
