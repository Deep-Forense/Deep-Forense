# Forensic API

Servicio FastAPI de ingesta y consulta. Implementa la primera capa del pipeline: valida entradas, almacena artefactos en MinIO, persiste jobs en MongoDB y publica tareas Celery en Redis.

## Arquitectura

```text
app/
├── domain/          Aggregate AnalysisJob, Artifact, value objects, eventos y puertos
├── application/     DTO, puertos de entrada y casos de uso
├── infrastructure/  REST, JWT, Mongo, MinIO, Celery, HTTPX y Pillow
└── main.py          Composition root de FastAPI
```

Dependencias principales: FastAPI/Uvicorn, Motor/PyMongo, Celery/Redis, MinIO, PyJWT, HTTPX, BeautifulSoup, Pillow y PyMuPDF.

## Endpoints

| Método y ruta | JWT | Notas |
|---|---:|---|
| `GET /health` | No | Liveness simple; no comprueba dependencias |
| `POST /api/forensic/demo/analyze` | No | Job sin propietario, detalle básico |
| `POST /api/forensic/analyze` | Sí | Job asociado al claim `userId` |
| `GET /api/forensic/jobs` | Sí | Historial propio; `page`, `page_size`, `verdict` |
| `GET /api/forensic/jobs/{job_id}` | Opcional | Completo solo para el propietario |
| `GET .../{artifact_id}/ela-heatmap` | Propietario | Devuelve `image/png` o 404 |

Los POST son `multipart/form-data` y exigen exactamente `file` o `url`. Un archivo puede ser PDF, JPEG, PNG o WEBP y no superar 50 MB. El PDF debe abrirse, tener páginas y no requerir contraseña. Una URL debe ser HTTP(S), descargar como máximo 50 MB y apuntar directamente a una imagen válida; el adaptador controla redirects y destinos SSRF.

Respuesta de creación:

```json
{"job_id":"uuid","status":"PENDING","artifacts_count":1}
```

## Persistencia y acceso

Los originales se guardan bajo `uploads/{uuid}-{nombre}`. Mongo usa la colección `analysis_jobs` y crea al arrancar el índice `{user_id: 1, created_at: -1}`. El detalle público/básico oculta origen, análisis, artefacto dominante y política; el propietario recibe `detail_level=full`.

El servicio decodifica el JWT compartido con Auth y toma `userId` (o `sub` como fallback). No valida tokens en Kong.

## Variables

`MONGO_URI`, `MONGO_DB`, `REDIS_URL`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `JWT_SECRET` y `ROOT_PATH`.

## Desarrollo

```bash
python -m venv .venv
# activar el entorno según el sistema operativo
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
pytest
```

MongoDB, Redis y MinIO deben estar disponibles con las variables configuradas para ejecutar la aplicación. Las pruebas usan dobles definidos en `tests/conftest.py` y cubren agregado, validación de upload, JWT, persistencia/eventos, índices, URL, selección y consultas.

## Operación

El endpoint health es solo liveness. Para readiness real se requieren comprobaciones de Mongo, Redis y MinIO. Si se guarda el artefacto o job pero falla el paso siguiente, actualmente puede quedar estado huérfano; monitorear excepciones de ingesta y reconciliar jobs `PENDING` antiguos.
