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

# Hugging Face Spaces menggunakan port 7860
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
