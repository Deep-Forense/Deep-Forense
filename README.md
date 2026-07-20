# DeepForense — documentación general

## 1. Propósito


DeepForense es una aplicación web distribuida para recibir imágenes, documentos PDF o una URL directa de imagen, ejecutar un análisis forense asíncrono y presentar un nivel de riesgo junto con las evidencias técnicas disponibles.

Esta documentación describe el código observado en el repositorio a 20 de julio de 2026. El contrato consolidado está en [`openapi.yaml`](./openapi.yaml) y los resultados de la revisión técnica en [`AUDITORIA_CODIGO.md`](./AUDITORIA_CODIGO.md).

Recorrido integral de la plataforma:

- [`FLUJO_COMPLETO_APLICACION.md`](./FLUJO_COMPLETO_APLICACION.md): entrada del usuario, frontend, registro/login, Kong, servicios, bases de datos, MinIO, Redis/Celery, procesamiento, polling, resultados, historial, errores y despliegue.

Flujos forenses detallados:

- [`FLUJO_ANALISIS_IMAGENES.md`](./FLUJO_ANALISIS_IMAGENES.md): archivo y URL, EXIF, ELA, DCT/Benford, Gemini, clasificación y cálculo completo.
- [`FLUJO_ANALISIS_DOCUMENTOS.md`](./FLUJO_ANALISIS_DOCUMENTOS.md): PDF, estructura/firmas, OCR, consistencia, DeepSeek, Benford, imágenes embebidas y resultado. También documenta que la URL de PDF aún no está soportada.

Fundamentos e implementación de algoritmos:

- [`ALGORITMOS_ANALISIS_IMAGENES.md`](./ALGORITMOS_ANALISIS_IMAGENES.md): magic bytes, EXIF, ELA, DCT, Benford, Gemini, clasificación, scoring y sus clases concretas.
- [`ALGORITMOS_ANALISIS_DOCUMENTOS.md`](./ALGORITMOS_ANALISIS_DOCUMENTOS.md): parsing PDF, firmas, OCR híbrido, normalización, consistencia, DeepSeek, Benford, análisis visual y ensamblaje en código.

## 2. Componentes

| Componente | Tecnología | Responsabilidad | Documentación |
|---|---|---|---|
| Frontend | React 18, Vite 6, Axios | Interfaz, autenticación, carga, polling e historial | [`frontend/README.md`](./frontend/README.md) |
| Kong Gateway | Kong 3.7, DB-less | Punto de entrada, rutas, CORS y rate limiting | [`kong/README.md`](./kong/README.md) |
| Forensic API | Python 3.11, FastAPI | Validación, ingesta, persistencia y encolado | [`forensic-api/README.md`](./forensic-api/README.md) |
| Forensic Worker | Python 3.11, Celery | Análisis técnico/cognitivo y consolidación | [`forensic-worker/README.md`](./forensic-worker/README.md) |
| Auth Service | Java 21, Spring Boot 3.3 | Registro, login, JWT y perfil | [`auth-service/README.md`](./auth-service/README.md) |

Infraestructura: PostgreSQL almacena usuarios; MongoDB, jobs forenses; Redis es broker/backend de Celery; MinIO almacena originales y heatmaps ELA.

## 3. Arquitectura y flujo

```text
Navegador
   │ HTTP/JWT
   ▼
Kong :8000 ─────► auth-service :8080 ─────► PostgreSQL
   │
   └────────────► forensic-api :8000 ──────► MongoDB
                         │                  ├► MinIO
                         └► Redis/Celery ──► forensic-worker
                                                ├► MongoDB / MinIO
                                                └► DeepSeek / Gemini
```

1. El usuario se registra o inicia sesión; `auth-service` emite un JWT HS256 con `sub=email` y `userId`.
2. El frontend envía un archivo o URL a Kong. La API valida bytes/formato, guarda el artefacto en MinIO, crea un job `PENDING` en MongoDB y publica `process_analysis_job` en Redis.
3. El worker cambia el job a `PROCESSING`, analiza sus artefactos en paralelo, persiste evidencias y consolida el resultado.
4. El frontend consulta el job cada 1,5 segundos hasta `COMPLETED`, `FAILED` o 40 intentos.
5. Los jobs autenticados ofrecen detalle completo e historial; los jobs demo muestran una vista básica.

Los servicios de negocio aplican una variante de arquitectura hexagonal: `domain` contiene reglas y puertos, `application` casos de uso, e `infrastructure` adaptadores y composición.

## 4. Puesta en marcha

### Requisitos

- Docker Engine y Docker Compose.
- Para ejecución nativa: Node.js 20, Java 21/Maven y Python 3.11.
- Claves externas opcionales para completar el análisis cognitivo.

```bash
cp .env.example .env
docker compose up --build
```

En PowerShell, el equivalente de la primera línea es:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Cambiar todas las credenciales y completar las API keys en `.env` antes de un despliegue real.

### URLs de desarrollo

| Recurso | URL |
|---|---|
| Frontend Vite | `http://localhost:5173` |
| API mediante Kong | `http://localhost:8000` |
| Kong Admin (solo override local) | `http://localhost:8001` |
| Swagger consolidado | `http://localhost:8085` |
| FastAPI Swagger vía Kong | `http://localhost:8000/forensic-docs/docs` |
| Auth Swagger vía Kong | `http://localhost:8000/auth-docs/swagger-ui.html` |
| MinIO consola | `http://localhost:9001` |

Para producción:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

El frontend queda en el puerto 80 y Kong en el 8000. Las bases de datos y el Admin API no se publican al host. El valor de `VITE_API_BASE_URL` se incorpora al bundle durante el build.

## 5. Variables de entorno

| Grupo | Variables |
|---|---|
| PostgreSQL | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| MongoDB | `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`, `MONGO_DB` |
| MinIO | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET` |
| JWT | `JWT_SECRET`, `JWT_EXPIRATION_MS` |
| Worker IA | `DEEPSEEK_*`, `DEEPSEEK_OCR_*`, `GEMINI_*` |
| Reglas | `BENFORD_MIN_AMOUNT_COUNT`, `PDF_MAX_*`, `PDF_IMAGE_ANALYSIS_CONCURRENCY`, `CONSOLIDATION_POLICY` |
| Frontend | `VITE_API_BASE_URL` |

Consulte `.env.example` para valores de desarrollo. No versionar `.env`.

## 6. API resumida

| Método y ruta | Acceso | Función |
|---|---|---|
| `POST /api/auth/register` | Público | Crear usuario |
| `POST /api/auth/login` | Público | Obtener JWT |
| `POST /api/auth/logout` | JWT | Descarte lógico del token |
| `GET /api/auth/me` | JWT | Perfil actual |
| `POST /api/forensic/demo/analyze` | Público | Crear análisis demo |
| `POST /api/forensic/analyze` | JWT | Crear análisis asociado al usuario |
| `GET /api/forensic/jobs` | JWT | Historial paginado propio |
| `GET /api/forensic/jobs/{id}` | Opcional | Estado y detalle básico/completo |
| `GET /api/forensic/jobs/{id}/artifacts/{artifactId}/ela-heatmap` | Propietario | PNG de evidencia ELA |

La ingesta acepta exactamente uno de `file` o `url`. Los archivos admitidos son PDF, JPEG, PNG y WEBP, con máximo de 50 MB. Una URL debe apuntar directamente a una imagen compatible.

## 7. Operación y pruebas

```bash
# API y worker
cd forensic-api && python -m pytest
cd ../forensic-worker && python -m pytest

# Auth
cd ../auth-service && mvn test

# Frontend
cd ../frontend && npm ci && npm run build

# Validar Compose
cd .. && docker compose config --quiet
```

Para observar la ejecución use `docker compose logs -f kong forensic-api forensic-worker auth-service`. Los datos viven en volúmenes Docker; `docker compose down` conserva datos y `docker compose down -v` los elimina.

## 8. Estados y resultados

Los jobs recorren `PENDING → PROCESSING → COMPLETED|FAILED`. Un job puede terminar `COMPLETED` si al menos un artefacto fue analizado; solo falla cuando todos fallan. Los veredictos consolidados son `APPROVED`, `SUSPICIOUS`, `REJECTED` o `INCONCLUSIVE`. Un resultado forense es una señal de apoyo y no sustituye una pericia humana.
