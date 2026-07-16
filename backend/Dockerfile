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

# Salin frontend files
COPY --chown=user ../frontend /app/frontend

# Port 7860 default (Hugging Face Spaces convention); Railway/Render inject their
# own $PORT at runtime, which this must respect — shell form (not exec form) is
# required so ${PORT:-7860} actually expands.
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-7860}
