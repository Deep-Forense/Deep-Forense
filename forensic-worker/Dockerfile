# DeepForense — forensic-worker (Python 3.11 + Celery)
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

# OpenCV necesita estas libs del sistema para decodificar imágenes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --create-home app

COPY --from=build /install /usr/local
WORKDIR /app
COPY app ./app
USER app

CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info"]
