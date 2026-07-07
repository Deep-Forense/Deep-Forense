# DeepForense

Plataforma web para detección de fraude y manipulación en contenido digital (imágenes, documentos, URLs).

## Estructura del repositorio

```txt
deepforense/
├── auth-service/       Java 21 + Spring Boot — Identity Context
├── forensic-api/       Python 3.11 + FastAPI — Capa 1 (Ingesta)
├── forensic-worker/    Python 3.11 + Celery — Capas 2 y 3 (Análisis + Consolidación)
├── frontend/           React + Vite + TypeScript
├── kong/               Configuración declarativa de Kong (kong.yml)
├── docs/               SRS, OpenAPI, arquitectura consolidada
├── docker-compose.yml
└── .env.example
```

Cada servicio de negocio (`auth-service`, `forensic-api`, `forensic-worker`) sigue **arquitectura hexagonal**:

```txt
domain/            Reglas de negocio puras — sin frameworks, sin DB, sin HTTP
application/        Casos de uso, orquesta el dominio
infrastructure/
  adapter/input/    Adaptadores de entrada (controladores REST, workers de Celery)
  adapter/output/   Adaptadores de salida (repos, clientes de MongoDB/MinIO/APIs externas)
```

## Requisitos previos

- Docker y Docker Compose
- (Opcional para desarrollo fuera de Docker) Java 21, Python 3.11, Node 20

## Cómo levantar el proyecto

```bash
git clone <repo-url>
cd deepforense
cp .env.example .env
# Completar .env con las API keys reales (DeepSeek, DeepSeek-OCR/DeepInfra, Gemini, Scrapfly)

docker compose up --build
```

Servicios expuestos:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Kong (entrada única de la API) | http://localhost:8000 |
| Kong Admin API (solo dev) | http://localhost:8001 |
| MinIO Consola | http://localhost:9001 |
| **Swagger UI unificado** (contrato completo, `docs/openapi.yaml`) | http://localhost:8085 |
| Swagger UI de forensic-api (FastAPI, autogenerado, vía Kong) | http://localhost:8000/forensic-docs/docs |
| Swagger UI de auth-service (springdoc, autogenerado, vía Kong) | http://localhost:8000/auth-docs/swagger-ui.html |

**Importante:** el frontend y cualquier cliente externo deben llamar siempre a través de Kong (`http://localhost:8000/...`), nunca directo a `auth-service` o `forensic-api`. Ambos servicios solo exponen su puerto dentro de la red interna de Docker (`expose`, sin `ports`), por lo que no son alcanzables directo desde el host. Kong enruta, además de `/api/auth/*` y `/api/forensic/*`, la documentación interactiva de cada servicio bajo `/auth-docs/*` y `/forensic-docs/*` (ver `kong/kong.yml`).

## Documentación

- `docs/deepforense_mvp_consolidado.md` — arquitectura completa (microservicios, DDD, pipeline de 3 capas)
- `docs/DeepForense_SRS.md` — especificación de requerimientos
- `docs/openapi.yaml` — contrato de API (importar en Postman/Swagger UI)

## Variables de entorno sensibles

Las siguientes requieren cuenta/API key propia (ver `.env.example`):

- `DEEPSEEK_API_KEY` — clasificación semántica de texto
- `DEEPSEEK_OCR_DEEPINFRA_API_KEY` — OCR de documentos (DeepSeek-OCR vía DeepInfra)
- `GEMINI_API_KEY` — análisis visual de imágenes
- `SCRAPFLY_API_KEY` — scraping de URLs con contenido HTML

## Estado del proyecto

Esqueleto inicial: contenedores, estructura hexagonal por servicio, y stubs de endpoints/tareas documentados con `TODO`. La lógica de negocio real (pipeline, scoring, consolidación) se implementa siguiendo `docs/deepforense_mvp_consolidado.md`.
