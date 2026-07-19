# Gunakan Python 3.10 sebagai base image
FROM python:3.10-slim

# Cipta user baru untuk keselamatan (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Salin requirements dan pasang dependencies
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Salin semua kod projek ke dalam container
COPY --chown=user . /app

# NOTE: this Dockerfile's build context is ./backend only — it cannot COPY
# ../frontend (Docker forbids reaching outside the build context; an
# earlier version of this line did exactly that and would fail every real
# `docker build`, not just look wrong). This image is therefore API-only:
# no dashboard is baked in. `docker-compose.yml` bind-mounts ./frontend at
# *runtime* for local dev, which is why this went unnoticed there. For a
# monolith deploy that serves the dashboard too (Railway, or Render with
# Root Directory set to the repo root), use the root ../Dockerfile instead
# — see docs/deployment.md.

# Port 7860 default (Hugging Face Spaces convention); Railway/Render inject their
# own $PORT at runtime, which this must respect — shell form (not exec form) is
# required so ${PORT:-7860} actually expands.
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-7860}
