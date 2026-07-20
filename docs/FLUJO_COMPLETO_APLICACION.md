# Flujo completo de la aplicación DeepForense

## 1. Propósito y alcance

Este documento recorre la aplicación desde que una persona abre la URL hasta que obtiene y consulta un resultado forense. Incluye navegación, autenticación, gateway, ingesta, almacenamiento, cola, worker, proveedores externos, persistencia, polling, historial, documentación y diferencias entre desarrollo y producción.

La descripción corresponde al código observado el 20 de julio de 2026. Los detalles matemáticos están en:

- [`FLUJO_ANALISIS_IMAGENES.md`](./FLUJO_ANALISIS_IMAGENES.md);
- [`FLUJO_ANALISIS_DOCUMENTOS.md`](./FLUJO_ANALISIS_DOCUMENTOS.md);
- [`ALGORITMOS_ANALISIS_IMAGENES.md`](./ALGORITMOS_ANALISIS_IMAGENES.md);
- [`ALGORITMOS_ANALISIS_DOCUMENTOS.md`](./ALGORITMOS_ANALISIS_DOCUMENTOS.md).

## 2. Vista completa de componentes

```text
┌──────────────────────────────── Navegador ────────────────────────────────┐
│ React SPA: landing, registro, login, dashboard, escáner, polling, reporte │
└───────────────┬──────────────────────────────┬────────────────────────────┘
                │ carga HTML/JS/CSS            │ HTTP / Bearer JWT
                ▼                              ▼
       Frontend Vite/Nginx               Kong Gateway :8000
                                                │
                              ┌─────────────────┴──────────────────┐
                              ▼                                    ▼
                    Auth Service :8080                    Forensic API :8000
                    Java/Spring Boot                       Python/FastAPI
                              │                         ┌──────────┼───────────┐
                              ▼                         ▼          ▼           ▼
                       PostgreSQL                    MongoDB     MinIO       Redis
                    usuarios/credenciales             jobs    artefactos    broker
                                                                      │
                                                                      ▼
                                                           Forensic Worker/Celery
                                                           ┌──────────┼─────────┐
                                                           ▼          ▼         ▼
                                                        MongoDB     MinIO    APIs IA
                                                                            │
                                                              DeepSeek/OCR/Gemini
```

El navegador no llama directamente a Auth Service ni Forensic API. Sus puertos solo están expuestos dentro de la red Docker. Kong es el punto de entrada para todas las llamadas API.

## 3. Responsabilidad de cada componente

| Componente | Responsabilidad | Tecnología | Dependencias directas |
|---|---|---|---|
| Frontend | Presentación, sesión local, formularios, polling e historial | React 18, Vite 6, Axios | Kong |
| Kong | Routing, CORS, prefijos de documentación y rate limit | Kong 3.7 DB-less | Auth, Forensic API |
| Auth Service | Usuarios, contraseñas, login, JWT y perfil | Java 21, Spring Boot, JPA, Security | PostgreSQL |
| Forensic API | Validación, descarga URL, MinIO, creación/consulta de jobs, publicación Celery | Python 3.11, FastAPI | MongoDB, MinIO, Redis |
| Forensic Worker | Análisis, scoring y consolidación | Python 3.11, Celery, OpenCV, Pillow, PyMuPDF | Redis, MongoDB, MinIO, proveedores IA |
| PostgreSQL | Persistencia transaccional de usuarios | PostgreSQL 16 | Auth Service |
| MongoDB | Documento completo del job, artefactos, eventos y resultado | MongoDB 7 | API y Worker |
| Redis | Broker y backend Celery | Redis 7 | API y Worker |
| MinIO | Originales y heatmaps | MinIO | API y Worker |

Los tres servicios de negocio siguen separación hexagonal: dominio y puertos, casos de uso y adaptadores de infraestructura.

## 4. Arranque de la plataforma

Al ejecutar `docker compose up --build`:

1. PostgreSQL, MongoDB, Redis y MinIO arrancan con volúmenes persistentes.
2. Redis habilita AOF con sincronización cada segundo y snapshots.
3. `minio-init` espera el healthcheck de MinIO, configura un alias y crea idempotentemente el bucket `deepforense-artifacts`.
4. Auth Service espera PostgreSQL saludable.
5. Forensic API espera MongoDB, Redis, MinIO y la terminación exitosa de `minio-init`.
6. Forensic Worker espera MongoDB, Redis y MinIO.
7. Kong depende de Auth Service y Forensic API.
8. Frontend depende de Kong.

Las condiciones de `depends_on` ordenan el arranque, pero Auth Service no tiene healthcheck propio y Kong solo declara dependencia, no espera readiness HTTP.

### Inicialización de servicios

- Auth Service conecta JPA con PostgreSQL y aplica actualmente `ddl-auto: update`.
- Forensic API crea clientes Motor, MinIO y Celery en su composition root; al startup crea el índice Mongo `{user_id:1, created_at:-1}`.
- Worker crea la aplicación Celery. Los clientes Mongo/MinIO se inicializan dentro de cada proceso hijo mediante señales `worker_process_init`, evitando reutilizar un cliente Mongo previo al fork.
- Kong carga `kong/kong.yml` en modo declarativo, sin base de datos propia.

## 5. Entrada inicial del usuario

### Desarrollo

El navegador abre `http://localhost:5173`. Vite sirve `index.html`, JavaScript y CSS, con hot reload.

### Producción

El navegador abre el host en el puerto 80. La imagen frontend se compila en una etapa Node y Nginx no privilegiado sirve los archivos estáticos desde el puerto interno 8080. `VITE_API_BASE_URL` queda incorporado en el bundle durante el build.

Nginx usa:

```text
try_files $uri $uri/ /index.html
```

Así, una navegación directa a `/login`, `/register` o `/dashboard` devuelve la SPA y React Router decide la pantalla.

## 6. Inicialización del frontend y rutas

`main.jsx` monta React y `AppRouter` configura:

| Ruta | Página | Acceso |
|---|---|---|
| `/` | Landing | Público |
| `/login` | Inicio de sesión | Público |
| `/register` | Registro | Público |
| `/dashboard` | Dashboard | Protección frontend |
| Cualquier otra | Landing | Público |

`ProtectedRoute` únicamente comprueba si existe `deepforense_token` en `localStorage`. Si no existe, redirige a `/login`; no valida expiración ni firma localmente. La validación verdadera ocurre en los microservicios cuando reciben el token.

El cliente Axios usa `VITE_API_BASE_URL` o `http://localhost:8000`. Antes de cada solicitud busca el token y, si existe, agrega:

```http
Authorization: Bearer <jwt>
```

No hay interceptor global para respuestas 401 ni renovación de token.

## 7. Landing y modo demo

La landing renderiza información comercial y `ForensicScannerCard` con `authenticated=false`. La persona puede:

- elegir modo documento o imagen;
- arrastrar/seleccionar un archivo;
- pegar una URL directa de imagen;
- ir a registro o login.

El frontend rechaza archivos superiores a 50 MiB. En modo documento exige extensión `.pdf`. El backend vuelve a validar por bytes; la validación del navegador es solo experiencia de usuario.

Para una URL, el frontend cambia internamente a modo imagen. Hoy no existe análisis de PDF por URL ni scraping de una página HTML: debe ser una URL directa JPEG, PNG o WEBP.

El análisis demo crea un job sin `user_id`. Cualquier consulta de ese job devuelve `detail_level=basic`, incluso si después se adjunta un JWT, porque no existe propietario asociado.

## 8. Registro de usuario

### 8.1 Interacción frontend

En `/register`, el navegador solicita:

- nombre;
- correo;
- contraseña de mínimo ocho caracteres;
- confirmación de contraseña;
- aceptación visual de términos.

El frontend verifica que ambas contraseñas coincidan y envía:

```http
POST /api/auth/register
Content-Type: application/json

{"name":"...","email":"...","password":"..."}
```

### 8.2 Paso por Kong

Kong encuentra `auth-routes`, conserva el path completo porque `strip_path=false` y reenvía a:

```text
http://auth-service:8080/api/auth/register
```

La ruta Auth completa tiene rate limiting local de 10 solicitudes por minuto. El plugin CORS responde a solicitudes cross-origin admitidas por su configuración.

### 8.3 Auth Service

`AuthController` crea `RegisterUserCommand`. `RegisterUserUseCase`:

1. Construye `Email`, valida formato y normaliza a minúsculas.
2. Comprueba duplicado mediante `UserRepositoryPort`.
3. Construye `RawPassword`, que exige al menos 8 caracteres.
4. Hashea con BCrypt mediante `BCryptPasswordHasherAdapter`.
5. `User.register()` valida nombre, genera UUID y fecha UTC, y crea un evento de dominio en memoria.
6. `JpaUserRepositoryAdapter` persiste en PostgreSQL mediante Spring Data JPA.

Respuestas: 201 al crear, 409 para correo registrado y 400 para datos inválidos.

### 8.4 Login automático tras registro

`registerAndLogin()` no usa el resultado del registro para autenticar. Al terminar ejecuta inmediatamente `POST /api/auth/login` con correo y contraseña. Si el login tiene éxito, guarda el JWT y redirige a `/dashboard`.

## 9. Inicio de sesión

El formulario de `/login` envía correo y contraseña a `/api/auth/login`. En Auth Service:

1. `Email` valida y normaliza.
2. El repositorio busca al usuario por email.
3. BCrypt compara contraseña cruda y hash.
4. Si falla cualquiera, devuelve 401 `INVALID_CREDENTIALS`.
5. `JwtTokenProviderAdapter` crea un JWT firmado con la clave HMAC compartida.

Claims:

```json
{
  "sub": "correo-normalizado",
  "userId": "uuid-del-usuario",
  "iat": "fecha-emisión",
  "exp": "fecha-expiración"
}
```

La respuesta incluye `access_token`, `token_type=Bearer`, `expires_in` y datos básicos del usuario. El frontend guarda:

- `deepforense_token`;
- `deepforense_user`.

Ambos se almacenan en `localStorage`, por lo que sobreviven a cerrar la pestaña. La casilla “Recordar sesión por 30 días” no cambia la persistencia ni expiración actual. Los botones sociales y “Olvidaste tu contraseña” tampoco tienen integración funcional implementada.

## 10. Autenticación entre microservicios

Auth Service y Forensic API reciben el mismo `JWT_SECRET` desde Compose.

- Auth Service emite y valida el token para `/api/auth/me` y `/logout`.
- Forensic API decodifica el Bearer con PyJWT, toma `userId` o `sub` como fallback y asocia/autoriza jobs.
- Kong no valida JWT; solo lo reenvía.
- Worker no recibe JWT: confía en el `user_id` ya persistido por Forensic API.

Las solicitudes forenses autenticadas fallan con 401 si no hay token válido. Las consultas opcionales ignoran un token inválido y degradan a vista básica.

## 11. Apertura del dashboard

Cuando React entra a `/dashboard`:

1. `ProtectedRoute` confirma que existe token local.
2. `DashboardPage` monta el scanner autenticado.
3. `useEffect` llama a `GET /api/forensic/jobs?page=1&page_size=10`.
4. Axios adjunta el Bearer.
5. Kong reenvía a Forensic API.
6. `require_user_id` extrae el UUID.
7. `ListJobsUseCase` consulta exclusivamente `user_id` en Mongo, ordena por `created_at` descendente y pagina con el índice compuesto.

El frontend calcula sobre la página visible:

- total de archivos usando el `total` del backend;
- promedio de riesgo de los últimos diez mostrados;
- cantidad sospechosa contando `SUSPICIOUS`, `REJECTED` e `INCONCLUSIVE`.

Los jobs demo no aparecen porque su `user_id` es nulo.

## 12. Selección y envío de un análisis

### 12.1 Decisión demo o autenticada

```text
authenticated=false → POST /api/forensic/demo/analyze
authenticated=true  → POST /api/forensic/analyze + JWT
```

El formulario multipart contiene exactamente uno:

- `file`: PDF/JPEG/PNG/WEBP;
- `url`: URL directa a JPEG/PNG/WEBP.

El parámetro visual `mode` no se envía al backend. El backend detecta el tipo por contenido real.

### 12.2 Kong hacia Forensic API

Kong encuentra `/api/forensic`, usa `strip_path=false` y reenvía a `http://forensic-api:8000`. No existe rate limit específico para estas rutas.

### 12.3 Validación de archivo

Forensic API:

- exige exactamente una fuente;
- rechaza vacío y tamaño superior a 50 MiB;
- identifica JPEG, PNG, WEBP o PDF por magic bytes;
- valida contenedor WEBP;
- abre PDF con PyMuPDF, rechaza corrupto, vacío o protegido.

### 12.4 Obtención por URL

`HttpxUrlDownloaderAdapter`:

- solo permite HTTP/HTTPS;
- bloquea localhost e IP no global;
- valida nuevamente cada redirect, máximo cinco;
- usa timeout de 30 segundos;
- limita streaming y Content-Length a 50 MiB.

`SubmitUrlAnalysisUseCase` exige firma JPEG/PNG/WEBP y decodificación correcta con Pillow. No admite HTML ni PDF.

## 13. Creación del job y persistencia inicial

Para archivo, `SubmitAnalysisUseCase`; para URL, `SubmitUrlAnalysisUseCase`. Ambos siguen:

1. Generar nombre seguro de objeto con UUID.
2. Guardar bytes en MinIO antes de crear/encolar.
3. Crear `Artifact` con UUID, tipo `IMAGE` o `TEXT`, estado `PENDING`, `storage_ref` y origen.
4. Crear `AnalysisJob` con UUID, `user_id` opcional, estado `PENDING` y fecha UTC.
5. Guardar en colección Mongo `analysis_jobs`.
6. Sembrar evento persistido `JOB_CREATED`.
7. Enviar a Redis una tarea por nombre: `process_analysis_job(job_id)`.

El documento Mongo inicial tiene forma conceptual:

```json
{
  "_id": "job-uuid",
  "user_id": "user-uuid-o-null",
  "status": "PENDING",
  "consolidated": null,
  "artifacts": [{
    "artifact_id": "artifact-uuid",
    "type": "IMAGE|TEXT",
    "storage_ref": "bucket/uploads/...",
    "status": "PENDING",
    "origin": "UPLOAD|DIRECT_URL",
    "analysis": null
  }],
  "created_at": "...",
  "completed_at": null,
  "events": [{"type":"JOB_CREATED","timestamp":"..."}]
}
```

Forensic API no importa el worker. `CeleryTaskQueueAdapter` publica únicamente el nombre de tarea y el `job_id`, desacoplando ambos servicios mediante Redis.

La API responde HTTP 202 inmediatamente; no espera el análisis.

## 14. Consumo por Forensic Worker

Cada proceso Celery escucha Redis. Al recibir `process_analysis_job`:

1. Construye un nuevo `ProcessAnalysisJobUseCase` con adapters concretos.
2. Ejecuta el pipeline async mediante `asyncio.run()`.
3. Consulta el estado Mongo.
4. Si no existe, devuelve `JOB_NOT_FOUND`.
5. Si ya no está `PENDING` o `PROCESSING`, no repite el trabajo.
6. Hace un update condicional `PENDING → PROCESSING` y agrega `JOB_PROCESSING`; esto evita duplicar el evento ante reintentos.
7. Carga el array de artefactos y los procesa concurrentemente con `asyncio.gather`.

Aunque la ingesta actual crea un artefacto, el modelo soporta varios y aísla sus fallos.

## 15. Pipeline de una imagen

El worker descarga el original desde MinIO y ejecuta:

1. EXIF con Pillow: software y fechas.
2. ELA con OpenCV: recompresión calidad 90, score y heatmap.
3. Guarda heatmap en MinIO bajo `jobs/{job}/artifacts/{artifact}/ela_heatmap.png`.
4. Si es JPEG, DCT por bloques 8×8 y Benford; PNG/WEBP quedan no aplicables.
5. Gemini analiza señales visibles de generación IA, inpainting, clonación, composición, iluminación, texto deformado o captura.
6. Las señales IA críticas requieren una segunda verificación HIGH.
7. `ImageClassificationService` produce `AI_GENERATED`, `AI_MODIFIED`, `SCREENSHOT`, `EDITED`, `AUTHENTIC` o `INCONCLUSIVE`.
8. `FraudScoringService` combina 70% promedio técnico y 30% factor de flags, respetando pisos semánticos.

Si Gemini falla, el análisis técnico continúa y queda `cognitive_available=false`. Si EXIF/ELA o un paso técnico no controlado falla, ese artefacto queda `FAILED`.

## 16. Pipeline de un PDF

El worker descarga el PDF y ejecuta:

1. PyMuPDF inspecciona metadatos, objetos, revisiones, contenido activo, capas, formularios, fuentes, archivos y solapamientos.
2. pyHanko valida firmas, integridad, confianza y permisos DocMDP.
3. Para las primeras `PDF_MAX_PAGES` —10 por defecto— extrae texto digital si hay al menos 50 caracteres por página.
4. Páginas con poco texto se rasterizan a 150 DPI y pasan por OCR remoto.
5. Imágenes embebidas seleccionadas también pasan por OCR.
6. `DocumentConsistencyService` valida subtotal+impuestos=total, cantidad×precio y suma de líneas.
7. DeepSeek analiza hasta 12.000 caracteres, clasifica tipo, extrae montos y flags cognitivas.
8. Flags de texto IA requieren segunda verificación.
9. Benford financiero se ejecuta solo para tipo apropiado, al menos 30 montos, rango de 100× y mínimo 50% valores únicos.
10. Hasta cinco imágenes embebidas se analizan con EXIF, ELA, DCT/Benford y Gemini; concurrencia IA predeterminada 2.
11. Se deduplican imágenes mediante SHA-256 y se identifica la evidencia visual dominante.
12. Scoring combina estructura, consistencia, Benford, visuales y flags.

Los fallos OCR/IA generan advertencias y análisis incompleto cuando existe evidencia local suficiente. Un fallo completo de un artefacto queda aislado.

## 17. Scoring por artefacto

Para cualquier artefacto:

```text
numeric_scores = valores presentes; null se excluye
flags = unión de flags distintas
flags_factor = min(1, cantidad_flags/3)
signal_mean = promedio(numeric_scores)
base = 0.70×signal_mean + 0.30×flags_factor
fraud_score = max(base, piso_semántico)
```

Pisos principales:

- imagen generada/modificada por IA: 0.75;
- imagen editada: 0.40;
- texto posiblemente generado: 0.65;
- texto posiblemente editado: 0.50.

Todos los scores se limitan a `[0,1]` y se redondean a cuatro decimales.

## 18. Consolidación del job

Se incluyen únicamente artefactos `COMPLETED`.

### Política predeterminada

`worst_case_dominates`: el mayor `fraud_score` determina el resultado y su artefacto se marca dominante.

### Política alternativa

`weighted_average`: promedio normalizado con pesos `IMAGE=0.70` y `TEXT=0.30`.

### Veredicto

```text
fraud_score < 0.40       → APPROVED
0.40 ≤ fraud_score ≤0.70 → SUSPICIOUS
fraud_score > 0.70       → REJECTED
```

```text
risk_percentage = round(fraud_score×100)
authenticity_percentage = round((1-fraud_score)×100)
```

Si OCR o análisis cognitivo está explícitamente no disponible, `analysis_complete=false`. Si el score normal sería `APPROVED`, el veredicto se cambia a `INCONCLUSIVE` y autenticidad queda `null`; una evidencia suficiente para sospechar o rechazar se conserva.

## 19. Escritura del resultado en MongoDB

Por cada artefacto, el worker actualiza:

- `artifacts.$.status` a `COMPLETED` o `FAILED`;
- `artifacts.$.analysis` con todas las señales cuando completó.

Al cerrar:

- job `COMPLETED` si al menos un artefacto completó;
- job `FAILED` si todos fallaron;
- `consolidated` con score, porcentajes, veredicto, completitud, dominante y política;
- `completed_at` con fecha UTC;
- evento `JOB_COMPLETED` o `JOB_FAILED`.

El original y los heatmaps permanecen en MinIO; Mongo almacena referencias, no los binarios grandes.

## 20. Polling desde el navegador

Inmediatamente después de recibir HTTP 202, el frontend llama:

```http
GET /api/forensic/jobs/{job_id}
```

Lo repite hasta 40 veces con intervalo de 1.500 ms, aproximadamente 60 segundos máximos.

En cada cambio observado crea un evento local de interfaz:

```text
PENDING    → JOB_CREATED
PROCESSING → JOB_PROCESSING
COMPLETED  → JOB_COMPLETED
FAILED     → JOB_FAILED
```

Este timeline usa el momento en que el navegador observó el estado. MongoDB guarda eventos reales con timestamps del backend, pero la respuesta actual de detalle no expone el array `events`; por eso la UI no consume esos timestamps persistidos.

Si llega `COMPLETED`, normaliza el resultado. Si llega `FAILED`, muestra error. Si vence el polling, indica que el análisis continúa; el job no se cancela y puede consultarse posteriormente.

## 21. Control de acceso al resultado

`GET /jobs/{id}` acepta JWT opcional:

- JWT válido y `job.user_id == token.userId`: `detail_level=full`;
- sin JWT, token inválido, otro usuario o job demo: `detail_level=basic`.

Vista básica:

- estado;
- datos consolidados limitados;
- identificador, tipo y estado de artefactos;
- oculta origen, análisis, artefacto dominante y política.

Vista completa:

- todas las señales técnicas/cognitivas;
- origen y análisis por artefacto;
- URLs protegidas de heatmaps;
- política y artefacto dominante.

El heatmap exige que `GetArtifactHeatmapUseCase` confirme que el usuario autenticado es propietario; en otro caso devuelve 404, evitando revelar existencia/acceso.

## 22. Presentación del resultado

`normalizeScanResult()` transforma el contrato backend al modelo visual:

- convierte score a porcentaje;
- calcula autenticidad si corresponde;
- selecciona artefactos de imagen/documento;
- traduce la política a texto explicativo;
- genera un resumen según veredicto;
- muestra clasificación visual, métricas, warnings y heatmap cuando están disponibles.

Usuario demo ve `ScanResult` básico. Usuario autenticado ve `AdvancedScanResult` con evidencia ampliada.

La etiqueta `AUTHENTIC` de imagen y el veredicto `APPROVED` no son una certificación. `AUTHENTIC` es una clasificación visual y `APPROVED` un umbral matemático global.

## 23. Historial y reapertura

Después de completar un análisis autenticado, el dashboard recarga la primera página del historial. `GET /jobs`:

- exige JWT;
- filtra siempre por propietario;
- acepta página 1+, tamaño 1–100 y filtro de veredicto;
- ordena de más reciente a más antiguo;
- devuelve resumen y total.

Al seleccionar una fila, el frontend llama a `getJobDetail(jobId)`, obtiene vista completa y abre un modal con `AdvancedScanResult`. La paginación visible usa tamaño 10.

## 24. Perfil y logout

`GET /api/auth/me` pasa por Spring Security:

1. `JwtAuthenticationFilter` lee Bearer.
2. Verifica firma y expiración.
3. Usa `sub` como principal.
4. El controlador busca el usuario por email y devuelve perfil.

`POST /api/auth/logout` responde 204. No existe sesión de servidor ni blacklist: el frontend elimina token y usuario local en `finally`. Un token copiado continúa válido hasta `exp`.

## 25. Rutas y plugins de Kong

| Ruta externa | Servicio interno | Tratamiento |
|---|---|---|
| `/api/auth/*` | `auth-service:8080` | Path intacto, rate limit 10/min local |
| `/api/forensic/*` | `forensic-api:8000` | Path intacto |
| `/auth-docs/*` | Auth | Elimina prefijo y añade `X-Forwarded-Prefix` |
| `/forensic-docs/*` | Forensic API | Elimina prefijo; FastAPI usa `ROOT_PATH` |

CORS global admite Accept, Authorization y Content-Type, credenciales y métodos comunes. La configuración actual contiene una regex que permite cualquier origen HTTP/HTTPS; está registrada como hallazgo de auditoría y debe cerrarse en producción.

## 26. Documentación API

En desarrollo existen tres vistas:

- Swagger unificado en `:8085`, montado desde `docs/openapi.yaml`;
- FastAPI Swagger mediante `/forensic-docs/docs`;
- Springdoc mediante `/auth-docs/swagger-ui.html`.

El Swagger unificado es un contenedor exclusivo del override local. Las rutas de documentación de cada microservicio sí permanecen en la configuración de Kong base y actualmente también existen en producción.

## 27. Manejo de errores por capa

### Frontend

Captura errores Axios, extrae mensajes API y los presenta. Un fallo de historial no bloquea el scanner. Un timeout de polling no cancela el job.

### Kong

Puede devolver errores de upstream, CORS o 429 por rate limit Auth.

### Auth

Devuelve códigos estructurados para email duplicado, datos inválidos y credenciales incorrectas. Otros errores usan manejo estándar Spring.

### Forensic API

Devuelve 400 para entrada/formato/URL, 401 para JWT requerido, 404 para job/heatmap y 413 para tamaño. Fallos de infraestructura durante almacenamiento, Mongo o encolado pueden producir 5xx.

### Worker

Captura errores por artefacto, registra stack trace y permite que continúen otros. Los proveedores cognitivos se degradan cuando está previsto. Si todos fallan, el job termina FAILED.

## 28. Datos y límites de confianza

| Dato | Ubicación | Acceso |
|---|---|---|
| Usuario, email, BCrypt hash | PostgreSQL | Auth Service |
| JWT | Navegador localStorage | Frontend/navegador |
| Job, user_id, scores, eventos | MongoDB | API/Worker |
| Original y heatmaps | MinIO | API/Worker; heatmap servido por API |
| Mensajes Celery/result backend | Redis | API/Worker |
| Imagen/texto enviado a IA | Proveedores externos | Worker por HTTPS |

No se envía la contraseña a Forensic API ni Worker. No se envía el JWT al Worker ni a proveedores IA. El contenido analizado sí sale hacia proveedores externos cuando se ejecuta OCR, análisis textual o visual; esto debe reflejarse en privacidad y consentimiento.

## 29. Configuración por entorno

### Base

Define servicios, red Compose implícita, volúmenes, variables y solo publica Kong 8000.

### Desarrollo (`docker-compose.override.yml`)

Se carga automáticamente y publica PostgreSQL 5432, Mongo 27017, Redis 6379, MinIO 9000/9001, Kong Admin 8001, Vite 5173 y Swagger 8085.

### Producción (`docker-compose.prod.yml`)

Se aplica explícitamente. Compila frontend, publica 80→8080 y no añade puertos de infraestructura/Admin. Kong conserva 8000 desde el archivo base.

Todos los contenedores comparten la red creada por Compose y se resuelven por nombre de servicio: `postgres`, `mongo`, `redis`, `minio`, `auth-service` y `forensic-api`.

## 30. Variables que conectan los servicios

| Integración | Variables principales |
|---|---|
| Auth → PostgreSQL | `SPRING_DATASOURCE_URL`, usuario y contraseña |
| Auth ↔ API | `JWT_SECRET` compartido |
| API/Worker → Mongo | `MONGO_URI`, `MONGO_DB` |
| API/Worker → Redis | `REDIS_URL` |
| API/Worker → MinIO | `MINIO_ENDPOINT`, access key, secret, bucket |
| Worker → DeepSeek | `DEEPSEEK_API_KEY`, base URL, modelo |
| Worker → OCR | `DEEPSEEK_OCR_*` |
| Worker → Gemini | `GEMINI_API_KEY`, modelo |
| Frontend → Kong | `VITE_API_BASE_URL` |

Cambiar un nombre interno o credencial en un lado sin actualizar el consumidor rompe esa integración.

## 31. Máquina de estados y eventos

```text
              ┌──────────── artefactos procesados ────────────┐
PENDING ─────► PROCESSING ────────────────────────────────────► COMPLETED
                    │
                    └──────── todos los artefactos fallan ────► FAILED
```

No existen transiciones de regreso. El agregado de dominio valida la máquina de estados; el repositorio del worker implementa actualizaciones Mongo idempotentes para la ejecución real.

Eventos persistidos: `JOB_CREATED`, `JOB_PROCESSING`, `JOB_COMPLETED` o `JOB_FAILED`. Existen además eventos de dominio en memoria, pero no hay event bus externo implementado; comentarios del código reservan esa evolución futura.

## 32. Secuencias resumidas

### Visitante demo

```text
Navegador → Frontend → selecciona archivo/URL
Frontend → Kong → Forensic API demo
API → MinIO → Mongo → Redis
Redis → Worker → MinIO/Mongo/APIs IA
Frontend → Kong → API (polling básico)
API → Mongo → resultado básico → Frontend
```

### Usuario autenticado

```text
Navegador → Frontend → Kong → Auth → PostgreSQL
Auth → JWT → Frontend/localStorage
Frontend → Kong → Forensic API + Bearer
API valida JWT → user_id → MinIO/Mongo/Redis
Worker analiza → Mongo/MinIO/IA
Frontend hace polling con JWT → detalle completo
Dashboard recarga historial del user_id
```

## 33. Funciones visibles pero no implementadas completamente

Para evitar confundir interfaz con backend existente:

- login/registro social: botones visuales sin OAuth;
- recuperar contraseña: botón sin flujo;
- recordar 30 días: checkbox sin efecto;
- selección `mode`: no viaja al backend;
- `useScanUpload`: hook vacío;
- `src/services/api.ts`: módulo vacío;
- revocación/refresh de JWT: no existe;
- documentos por URL o scraping web: no existe;
- cancelación de jobs: no existe;
- exposición de eventos Mongo al frontend: no existe;
- event bus de eventos de dominio: no existe.

## 34. Resultado operativo completo

El flujo se considera terminado cuando:

1. el job está `COMPLETED` o `FAILED` en Mongo;
2. cada artefacto tiene estado final;
3. un job completado tiene objeto `consolidated`;
4. el frontend presenta el resultado o permite recuperarlo desde historial;
5. originales/evidencias permanecen en MinIO y la trazabilidad de estados en Mongo.

La aplicación entrega estimaciones y evidencias explicables. La decisión final debe considerar disponibilidad de proveedores, warnings, señales individuales y contexto humano; el porcentaje de autenticidad no es una garantía criptográfica ni jurídica.
