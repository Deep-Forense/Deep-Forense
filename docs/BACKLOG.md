# DeepForense — Backlog / Plan de Tareas

Basado en las prioridades del documento consolidado (sección 15) y dividido por integrante (sección 14). Cada tarea trae un criterio de aceptación verificable — la idea es poder marcarla como "hecha" sin ambigüedad.

Convención de estado: `[ ]` pendiente · `[~]` en progreso · `[x]` hecho

---

## Sprint 0 — Fundacional (bloquea a todo lo demás)

Debe completarse antes de repartir trabajo en paralelo, porque todos dependen de esto.

- [ ] **T0.1** — Levantar `docker compose up` con todos los contenedores de infraestructura corriendo (Postgres, Mongo, Redis, MinIO, Kong)
  - *Criterio de aceptación:* `docker compose ps` muestra los 5 contenedores en estado `healthy`/`running`.
- [ ] **T0.2** — Crear el bucket de MinIO (`deepforense-artifacts`) al iniciar
  - *Criterio de aceptación:* el bucket existe y es accesible desde la consola de MinIO (`localhost:9001`).
- [ ] **T0.3** — Validar que Kong enruta correctamente `/api/auth/*` y `/api/forensic/*` hacia los stubs de cada servicio
  - *Criterio de aceptación:* `curl http://localhost:8000/api/forensic/jobs/abc` responde (aunque sea 404 del stub), no error de Kong.
- [ ] **T0.4** — Todos los integrantes acuerdan el contrato de `docs/openapi.yaml` (revisar y ajustar si hace falta antes de programar)
  - *Criterio de aceptación:* el archivo se puede importar sin errores en Postman o Swagger UI.

---

## Sprint 1 — Flujo mínimo de punta a punta (sin IA real todavía)

Objetivo: que un archivo suba, se cree un job, y llegue "algo" de vuelta — aunque el análisis sea un mock. Esto valida que la tubería completa (frontend → Kong → forensic-api → Redis → forensic-worker → Mongo) funciona antes de meterle inteligencia real.

### Integrante 1 — Frontend

- [ ] **T1.F1** — Pantalla de landing con formulario de upload (archivo o URL)
  - *Aceptación:* el formulario llama a `POST /api/forensic/demo/analyze` y muestra el `job_id` recibido.
- [ ] **T1.F2** — Polling del estado del job (`GET /api/forensic/jobs/{job_id}`) cada 2-3 segundos hasta `COMPLETED`/`FAILED`
  - *Aceptación:* la UI pasa de "procesando" a mostrar el resultado sin recargar la página.
- [ ] **T1.F3** — Pantalla de resultado básico (veredicto + porcentajes)
  - *Aceptación:* se ve correctamente incluso con datos mock del backend.

### Integrante 2 — Plataforma

- [ ] **T1.P1** — `auth-service`: endpoint `POST /api/auth/register` funcional contra PostgreSQL
  - *Aceptación:* un registro duplicado responde 409; uno válido responde 201 y persiste en la tabla `users`.
- [ ] **T1.P2** — `auth-service`: endpoint `POST /api/auth/login` que emite JWT válido
  - *Aceptación:* el JWT decodificado contiene `sub` (user id) y expira según `JWT_EXPIRATION_MS`.
- [ ] **T1.P3** — `auth-service`: endpoint `GET /api/auth/me` protegido por JWT
  - *Aceptación:* sin token responde 401; con token válido responde los datos del usuario.
- [ ] **T1.P4** — Kong con CORS habilitado para el origen del frontend
  - *Aceptación:* una petición desde `localhost:5173` no es bloqueada por CORS en el navegador.

### Integrante 3 — Motor forense

- [ ] **T1.M1** — `forensic-api`: `POST /api/forensic/demo/analyze` crea el job en MongoDB con `status: PENDING` y **al menos 1 artifact** (sin scraping todavía, solo archivo directo)
  - *Aceptación:* el documento aparece en la colección `analysis_jobs` con la estructura de `artifacts: []` definida en el consolidado.
- [ ] **T1.M2** — El archivo subido se guarda en MinIO antes de encolar la tarea
  - *Aceptación:* el objeto existe en el bucket bajo la ruta `jobs/{job_id}/...`.
- [ ] **T1.M3** — La tarea se encola en Redis y `forensic-worker` la consume
  - *Aceptación:* logs del worker muestran la recepción del `job_id`.
- [ ] **T1.M4** — `forensic-worker` marca el job como `COMPLETED` con un resultado **mock** (fraud_score fijo, sin IA real todavía)
  - *Aceptación:* `GET /api/forensic/jobs/{job_id}` refleja el cambio de estado y un `consolidated` con datos de prueba.

---

## Sprint 2 — Pipeline real (Capa 2: análisis técnico y de IA)

### Integrante 3 — Motor forense

- [ ] **T2.M1** — Adaptador `ExifToolAdapter`/`PillowExifAdapter` (`ExifAnalyzerPort`) — `exif_score` real por artifact IMAGE
- [ ] **T2.M2** — Adaptador `OpenCvElaAdapter` (`ElaAnalyzerPort`) — genera `ela_score` + heatmap guardado en MinIO
- [ ] **T2.M3** — Adaptador `OpenCvDctAdapter` + `BenfordStatisticalAdapter` (`DctAnalyzerPort`/`BenfordAnalyzerPort`) — `dct_benford_score`, con regla JPEG vs no-JPEG
- [ ] **T2.M4** — Adaptador `DeepSeekOcrAdapter` (`OcrPort`, vía DeepInfra) — extrae texto de artifacts TEXT provenientes de documentos
- [ ] **T2.M5** — Adaptador `DeepSeekAnalyzerAdapter` (`TextCognitiveAnalyzerPort`) — `document_type`, `financial_amounts`, `ai_flags`
- [ ] **T2.M6** — Adaptador `GeminiVisionAnalyzerAdapter` (`ImageCognitiveAnalyzerPort`) — `gemini_flags`
- [ ] **T2.M7** — `BenfordApplicabilityService` — decide si Benford aplica (texto: `document_type` + `amount_count` ≥ umbral; imagen: formato JPEG)
  - *Aceptación:* un texto no financiero nunca produce `benford_score`, sino `benford_applicable: false`.
- [ ] **T2.M8** — Procesamiento en paralelo de artifacts dentro de un mismo job (`asyncio.gather` o tareas Celery hijas)
  - *Aceptación:* un artifact que lanza excepción se marca `FAILED` sin detener a los demás.

Cada tarea de este sprint debe incluir su prueba unitaria mockeando la API externa correspondiente (no gastar cuota real de DeepSeek/Gemini en cada test).

---

## Sprint 3 — Ingesta avanzada y consolidación (Capa 1 y Capa 3)

### Integrante 3 — Motor forense

- [ ] **T3.M1** — Integración con Scrapfly para scraping de URLs con HTML
- [ ] **T3.M2** — `ArtifactSelectionService` — filtro de relevancia de imágenes (dimensiones mínimas, deduplicación por hash perceptual, posición en el DOM, límite `MAX_IMAGES_PER_JOB`)
- [ ] **T3.M3** — Creación de artifacts múltiples desde una URL (1 TEXT + N IMAGE)
  - *Aceptación:* una URL de prueba con texto e imágenes genera un job con más de un artifact.
- [ ] **T3.M4** — `ConsolidationService` con política `worst_case_dominates`
  - *Aceptación:* si cualquier artifact resulta `REJECTED`, el `consolidated.verdict` del job es `REJECTED`, y `dominant_artifact` apunta al artifact correcto.
- [ ] **T3.M5** — Registro de eventos del job (`JOB_CREATED`, `JOB_COMPLETED`, `JOB_FAILED`)

### Integrante 1 — Frontend

- [ ] **T3.F1** — Login/registro conectado a `auth-service`
- [ ] **T3.F2** — Dashboard autenticado con historial (`GET /api/forensic/jobs`)
- [ ] **T3.F3** — Vista de reporte detallado por artifact (scores parciales, flags, mapa ELA)

---

## Sprint 4 — Endurecimiento y demo final

- [ ] **T4.1** — Manejo de errores end-to-end (archivo corrupto, URL inaccesible, API externa caída)
- [ ] **T4.2** — Límites de recursos aplicados (PDF 1-2 páginas, tamaño máximo de imagen antes de Gemini)
- [ ] **T4.3** — Variables de entorno documentadas y `.env.example` actualizado si cambió algo
- [ ] **T4.4** — Prueba de extremo a extremo con al menos 3 casos reales: imagen manipulada conocida, documento financiero con montos, URL con contenido mixto
- [ ] **T4.5** — Preparar la demo (guion de qué mostrar, casos de prueba preparados de antemano)

---

## Fuera del backlog (mejora futura, no planificar todavía)

Ver `docs/deepforense_mvp_consolidado.md` sección 15 ("Prioridad baja o mejora futura") y `docs/DeepForense_SRS.md` sección 6: ChromaDB/embeddings, API keys, roles, panel admin, webhooks, C2PA, reportes PDF descargables.
