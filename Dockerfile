# Gunakan Python 3.10 sebagai base image
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

# Salin folder frontend ke dalam /app/frontend untuk disajikan sebagai monolith
COPY --chown=user frontend/ /app/frontend/

# Port akan disuntikkan secara dinamik oleh Railway/Render, default ke 7860
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-7860}
