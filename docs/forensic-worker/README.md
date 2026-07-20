# Forensic Worker

Worker Celery que consume `process_analysis_job(job_id)` desde Redis y ejecuta las capas de análisis y consolidación del pipeline.

## Flujo

1. Carga el job de MongoDB y lo marca `PROCESSING`.
2. Descarga cada artefacto desde MinIO y los procesa concurrentemente.
3. Para imágenes calcula EXIF, ELA, DCT/Benford cuando aplica y señales visuales de Gemini.
4. Para PDF revisa estructura, extrae/OCR texto, consistencia documental, señales semánticas, Benford financiero cuando aplica e imágenes embebidas.
5. Calcula fraude por artefacto y consolida por `worst_case_dominates` o `weighted_average`.
6. Persiste análisis, referencias a heatmaps y estado final en MongoDB.

Si una IA externa falla, se conservan señales técnicas y advertencias. Un job termina `COMPLETED` cuando al menos un artefacto concluye y `FAILED` solo si todos fallan.

## Arquitectura

`domain` contiene entidades, puertos y servicios puros de clasificación, consistencia, Benford, scoring y consolidación. `application/use_cases/process_analysis_job_use_case.py` orquesta. Los adaptadores de `infrastructure` conectan MongoDB, MinIO, Pillow, OpenCV, PyMuPDF, DeepSeek/OpenAI-compatible y Gemini. `app/worker.py` es composition root y entrada Celery.

Los clientes Mongo/MinIO se inicializan después del fork mediante señales Celery. El caso de uso se construye por tarea para no compartir clientes HTTP async entre event loops.

## Variables

| Variable | Default relevante |
|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` |
| `MONGO_URI`, `MONGO_DB` | Mongo local / `deepforense_forensic` |
| `MINIO_*` | MinIO local / bucket `deepforense-artifacts` |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | Análisis textual |
| `DEEPSEEK_OCR_*` | Extracción/OCR compatible con OpenAI |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Análisis visual |
| `BENFORD_MIN_AMOUNT_COUNT` | `30` |
| `PDF_MAX_PAGES` | `10` |
| `PDF_MAX_EMBEDDED_IMAGES` | `5` |
| `PDF_IMAGE_ANALYSIS_CONCURRENCY` | `2` |
| `CONSOLIDATION_POLICY` | `worst_case_dominates` |

Sin claves de IA, los adapters cognitivos fallan de manera controlada, pero el resultado puede ser inconcluso o incompleto.

## Desarrollo y operación

```bash
pip install -r requirements-dev.txt
celery -A app.worker worker --loglevel=info --concurrency=4
pytest
```

Compose usa concurrencia 4. Ajustarla según CPU, memoria, límites de proveedores y concurrencia interna de PDF. Redis tiene AOF/snapshots, pero no hay configuración explícita de reintentos, dead-letter queue o límites de tiempo de tarea; deben añadirse antes de cargas no controladas. Monitorear profundidad de cola, tiempo por job, fallos por adapter, uso de memoria y consumo/cuotas de APIs.

La suite incluye pruebas de pipeline, repositorio/eventos, ELA, EXIF, DCT/Benford, PDF, OCR, DeepSeek, Gemini, scoring, consistencia, clasificación y consolidación.
