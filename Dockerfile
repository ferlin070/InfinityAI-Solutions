# Stage 1: build the React dashboard (frontend-react/) into frontend/src/.
# frontend-react/vite.config.js's outDir already points at ../frontend/src
# relative to frontend-react/ — mirroring that same relative layout here
# (frontend-react/ next to frontend/) makes the build land in the right
# place without any extra copy/move step.
FROM node:22-alpine AS frontend-build
WORKDIR /repo
COPY frontend-react/package.json frontend-react/package-lock.json frontend-react/
RUN npm --prefix frontend-react ci
COPY frontend-react/ frontend-react/
RUN npm --prefix frontend-react run build

# Stage 2: Python backend, serving the built dashboard as a monolith.
FROM python:3.10-slim

# Cipta user baru untuk keselamatan (Hugging Face / standard container security)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Salin requirements dari folder backend dan pasang dependencies
COPY --chown=user backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Salin semua kod backend ke dalam /app
COPY --chown=user backend/ /app/

# Salin hasil build dashboard (bukan source repo frontend-react/) — lihat
# stage 1 di atas. get_frontend_dir() (backend/src/core/config.py) baca
# WORKDIR/frontend/src, jadi laluan destinasi mesti sepadan tepat.
COPY --chown=user --from=frontend-build /repo/frontend/src /app/frontend/src

# Port akan disuntikkan secara dinamik oleh Railway/Render, default ke 7860
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-7860}
