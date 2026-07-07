# DeepForense — forensic-worker (Python 3.11 + Celery)
FROM python:3.11-slim

# OpenCV necesita estas libs del sistema para decodificar imágenes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app

CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info"]
