# DeepForense — Documento Consolidado del Proyecto (MVP + Correcciones v2.1)

**Proyecto:** DeepForense / ForensicVerify Platform
**Tipo:** Aplicación web con microservicios y motor forense asíncrono
**Versión del documento:** MVP consolidado — integra el contexto general (v1) con las correcciones de arquitectura del pipeline (v2.1: modelo de artifacts múltiples, reglas de aplicabilidad de Benford, ELA reintegrado)
**Equipo:** 3 integrantes

---

## 1. Propósito del documento

Este documento reemplaza y consolida los dos documentos anteriores del proyecto (contexto general MVP + arquitectura de 3 capas corregida) en una sola fuente de verdad, para que todos los integrantes trabajen sobre la misma visión técnica y funcional, sin tener que cruzar información entre archivos separados.

Aquí se describe:

- Qué problema resuelve el sistema.
- Cómo funcionará la aplicación web.
- Qué microservicios se mantienen.
- Qué tecnologías se usarán.
- Cómo se conectan los servicios.
- Cómo se modela un job con múltiples artifacts (corrección v2).
- Qué algoritmos se usan en el motor forense, organizados en 3 capas.
- Cuándo se aplica la Ley de Benford y cuándo no (corrección v2).
- Cómo se aplicará arquitectura hexagonal.
- Cómo se aplicará Domain Driven Design.
- Cómo dividir el trabajo inicial entre 3 integrantes.

---

## 2. Visión general del proyecto

**DeepForense** será una plataforma web para analizar archivos digitales y URLs, determinando si presentan señales de manipulación, fraude o alteración.

El sistema permite recibir como entrada:

- Una imagen.
- Un documento (PDF).
- Una URL.

### 2.1 Modelo de artifacts (corregido en v2)

La regla original del MVP era "un job = un artifact principal", asumiendo que un job solo podía ser de un tipo (`PHOTO` **o** `DOCUMENT`). Esa regla se corrigió porque falla en un caso muy común: una URL real (anuncio, publicación, noticia, landing de estafa) casi siempre combina texto **y** varias imágenes al mismo tiempo. Forzar una sola rama de análisis implica perder información.

**Regla vigente:** un job **no tiene un solo tipo** — un job contiene una **lista de artifacts**, y cada artifact se procesa por el pipeline correspondiente a su tipo (`TEXT` o `IMAGE`). Al final, la Capa 3 consolida los resultados de todos los artifacts en un veredicto único.

```txt
Job
 └── artifacts: [ ]
       ├── artifact TEXT   → rama de texto (DeepSeek)
       ├── artifact IMAGE  → rama de imagen (EXIF + ELA + DCT + Gemini)
       ├── artifact IMAGE  → rama de imagen (EXIF + ELA + DCT + Gemini)
       └── ...
```

Ejemplos:

```txt
Caso 1: El usuario sube una imagen JPG
→ Se crea un job con 1 artifact de tipo IMAGE

Caso 2: El usuario sube un PDF
→ Se crea un job con 1 artifact de tipo TEXT/DOCUMENT

Caso 3: El usuario pega una URL que apunta directo a una imagen
→ Se crea un job con 1 artifact de tipo IMAGE

Caso 4: El usuario pega una URL que apunta directo a un PDF
→ Se crea un job con 1 artifact de tipo TEXT/DOCUMENT

Caso 5: El usuario pega una URL de una página HTML (el caso más común)
→ Se hace scraping del DOM
→ Se crea 1 artifact TEXT con el texto principal de la página
→ Se crean hasta N artifacts IMAGE con las imágenes relevantes del contenido
   (aplicando un filtro de relevancia antes de crearlos — ver sección 8.1)
```

El sistema devolverá un resultado con:

- Porcentaje de autenticidad.
- Porcentaje de riesgo.
- Fraud Score consolidado.
- Veredicto final.
- Señales detectadas por cada artifact.
- Reporte básico o detallado según el usuario haya iniciado sesión.

---

## 3. Alcance reducido del MVP

El proyecto original contemplaba más servicios y tecnologías. Para la primera versión, se redujo el alcance con el objetivo de hacerlo viable y más ligero.

### 3.1 Se mantiene

```txt
Frontend web
Kong API Gateway
auth-service
forensic-api
forensic-worker
MongoDB
PostgreSQL
Redis
MinIO
OCR básico
DeepSeek
Gemini Vision
EXIF
ELA
DCT
Benford cuando aplique (reglas de aplicabilidad corregidas — ver sección 9)
Eventos dentro del job
Modelo de artifacts múltiples por job (corrección v2)
```

### 3.2 Se elimina para el MVP

```txt
user-service
apikey-service
audit-service
roles
admin dashboard
enterprise
webhooks
ChromaDB
embeddings
CLIP
sentence-transformers
similarity_score
cambio de contraseña
```

**Nota importante (v2.1):** la primera versión del documento de arquitectura de 3 capas había reintroducido ChromaDB y embeddings (Hugging Face: `sentence-transformers`/CLIP) como "señal alternativa" para detectar texto o imágenes reciclados de fraudes anteriores. Esto contradecía la reducción de alcance definida aquí. **Se revierte esa decisión**: ChromaDB y los embeddings quedan fuera del MVP y se mantienen como mejora futura (sección 3.3). Cuando un artifact de texto no es financiero y Benford no aplica, el sistema se apoya únicamente en los flags que ya produce DeepSeek (lenguaje de urgencia, contradicciones internas, redacción tipo plantilla) — sin capa de memoria vectorial.

### 3.3 Se deja como mejora futura

```txt
ChromaDB
memoria vectorial (embeddings con Hugging Face: sentence-transformers / CLIP)
similarity_score (detección de contenido reciclado de fraudes anteriores)
API keys
servicio de auditoría independiente
roles de usuario
panel administrativo
C2PA
análisis avanzado de ruido del sensor
webhooks
planes enterprise
```

---

## 4. Arquitectura general reducida

La arquitectura se mantiene basada en microservicios, pero con menos servicios que la propuesta original.

```txt
Frontend Web
    ↓
Kong API Gateway
    ↓
┌───────────────────────┐
│ auth-service           │  Spring Boot + PostgreSQL
│ Registro / login / me  │
└───────────────────────┘

┌───────────────────────┐
│ forensic-api           │  FastAPI + MongoDB + MinIO + Redis
│ Recibe archivo o URL   │
│ Crea jobs y artifacts  │
│ Filtra imágenes        │
│ Consulta resultados    │
└───────────────────────┘
          ↓
┌───────────────────────┐
│ forensic-worker        │  Python + Celery
│ Ejecuta análisis por   │
│ artifact (paralelo)    │
│ OCR / EXIF / ELA / DCT │
│ DeepSeek / Gemini      │
│ Consolida Fraud Score  │
└───────────────────────┘
```

---

## 5. Microservicios del MVP

## 5.1 Kong API Gateway

Kong será el punto único de entrada hacia el backend.

El frontend no llamará directamente a cada microservicio, sino que llamará a Kong.

Ejemplo:

```txt
/api/auth/*      → auth-service
/api/forensic/*  → forensic-api
```

Responsabilidades:

- Centralizar las rutas.
- Aplicar CORS.
- Servir como entrada única del sistema.
- Facilitar futuras mejoras de seguridad.
- Permitir agregar rate limiting en una fase posterior.

En el MVP, Kong no validará API keys porque el `apikey-service` fue eliminado.

---

## 5.2 auth-service

Servicio encargado de la autenticación.

Tecnología:

```txt
Java 21
Spring Boot 3.x
Spring Security
Spring Data JPA
PostgreSQL
JWT
BCrypt
```

Responsabilidades del MVP:

```txt
Registrar usuario
Iniciar sesión
Cerrar sesión
Consultar usuario autenticado
Generar JWT
Validar credenciales
Guardar usuarios en PostgreSQL
```

Endpoints sugeridos:

```http
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

No incluye:

```txt
Cambio de contraseña
Recuperación de contraseña
Roles
Gestión de usuarios
```

---

## 5.3 forensic-api

Servicio encargado de recibir solicitudes de análisis y de la **Capa 1 (Ingesta y Extracción)** del pipeline.

Tecnología:

```txt
Python 3.11
FastAPI
Pydantic
MongoDB
MinIO
Redis
```

Responsabilidades:

```txt
Recibir archivo o URL
Validar si el usuario está autenticado o es demo pública
Crear el job de análisis
Crear la lista de artifacts (1 o varios, según el tipo de entrada)
Si es URL con página HTML: hacer scraping del DOM (Scrapfly)
Extraer texto principal -> artifact TEXT
Extraer imágenes candidatas del DOM
Aplicar filtro de relevancia antes de crear artifacts IMAGE
Guardar archivo o contenido de cada artifact en MinIO
Guardar estado inicial del job en MongoDB
Encolar tarea en Redis
Consultar estado del job
Consultar resultado del job
Registrar eventos básicos dentro del job
```

Endpoints sugeridos:

```http
POST /api/forensic/demo/analyze
POST /api/forensic/analyze
GET  /api/forensic/jobs/{job_id}
GET  /api/forensic/jobs
```

Diferencia entre demo y usuario autenticado:

```txt
Demo pública:
- No requiere login.
- user_id = null.
- Devuelve resultado básico.
- No muestra reporte técnico completo.

Usuario autenticado:
- Requiere JWT.
- user_id = id del usuario.
- Guarda historial.
- Muestra reporte detallado.
```

---

## 5.4 forensic-worker

Servicio encargado de ejecutar el análisis forense real: **Capa 2 (Análisis Cognitivo y Técnico)** y **Capa 3 (Consolidación)** del pipeline.

Tecnología:

```txt
Python 3.11
Celery
Redis
OpenCV
DeepSeek-OCR (vía DeepInfra) para OCR
ExifTool o Pillow
DeepSeek API (clasificación de texto)
Gemini Vision API
NumPy / SciPy
MongoDB
MinIO
```

Responsabilidades:

```txt
Consumir jobs desde Redis
Marcar job como PROCESSING
Descargar cada artifact desde MinIO
Procesar cada artifact de forma independiente (en paralelo si es posible)
Ejecutar pipeline según tipo de artifact (TEXT o IMAGE)
Calcular scores parciales por artifact
Marcar un artifact individual como FAILED sin tumbar el job completo
Aplicar ConsolidationService sobre todos los artifacts del job
Calcular Fraud Score final consolidado
Guardar resultado en MongoDB
Marcar job como COMPLETED o FAILED
Registrar eventos dentro del job
```

---

## 6. Bases de datos y almacenamiento

## 6.1 PostgreSQL

Usado por `auth-service`.

Responsabilidad:

```txt
Guardar usuarios registrados
Guardar credenciales hasheadas
Guardar datos mínimos de sesión si se requiere
```

Tabla principal sugerida:

```txt
users
├── id
├── name
├── email
├── password_hash
├── created_at
└── updated_at
```

---

## 6.2 MongoDB

Usado por `forensic-api` y `forensic-worker`.

Responsabilidad:

```txt
Guardar jobs
Guardar la lista de artifacts de cada job
Guardar estados (a nivel de job y a nivel de artifact)
Guardar resultados parciales por artifact y el resultado consolidado
Guardar eventos internos del análisis
```

Colección sugerida:

```txt
analysis_jobs
```

**Esquema actualizado (modelo de artifacts múltiples, corrección v2):**

```json
{
  "_id": "job-uuid",
  "user_id": "user-uuid o null",
  "status": "PENDING | PROCESSING | COMPLETED | FAILED",
  "input_source": "UPLOAD | URL",
  "original_url": "https://... (si aplica)",
  "artifacts": [
    {
      "artifact_id": "a1",
      "type": "TEXT",
      "origin": "UPLOAD | SCRAPED_DOM",
      "content_ref": "jobs/job-uuid/text_a1.txt",
      "analysis": {
        "document_type": "FINANCIAL_INVOICE",
        "financial_amounts": [1200.50, 340.00, 89.99],
        "amount_count": 3,
        "ai_flags": ["urgency_language"],
        "benford_applicable": true,
        "benford_score": 0.31
      }
    },
    {
      "artifact_id": "a2",
      "type": "IMAGE",
      "origin": "UPLOAD | SCRAPED_DOM_IMAGE",
      "storage_path": "jobs/job-uuid/img_a2.jpg",
      "analysis": {
        "exif_score": 0.10,
        "ela_score": 0.66,
        "dct_benford_score": 0.72,
        "gemini_flags": ["cloning_artifact", "inconsistent_lighting"]
      }
    }
  ],
  "consolidated": {
    "fraud_score": 0.68,
    "authenticity_percentage": 32,
    "risk_percentage": 68,
    "verdict": "SUSPICIOUS",
    "dominant_artifact": "a2",
    "policy_applied": "worst_case_dominates"
  },
  "events": [
    {
      "type": "JOB_CREATED",
      "timestamp": "2026-07-01T10:00:00Z"
    },
    {
      "type": "JOB_COMPLETED",
      "timestamp": "2026-07-01T10:00:30Z"
    }
  ],
  "created_at": "2026-07-01T10:00:00Z",
  "completed_at": "2026-07-01T10:00:30Z"
}
```

Diferencia clave respecto a la versión original: `artifact` (singular) pasó a ser `artifacts` (lista), y el bloque `consolidated` ahora indica explícitamente qué política de consolidación se aplicó y cuál fue el artifact que determinó el veredicto (`dominant_artifact`).

---

## 6.3 Redis

Usado como cola de tareas para Celery.

Responsabilidad:

```txt
Recibir tareas pendientes
Permitir que forensic-worker procese en segundo plano
Evitar que forensic-api se bloquee ejecutando análisis pesados
```

Flujo:

```txt
forensic-api crea job con su lista de artifacts
    ↓
forensic-api encola task en Redis
    ↓
forensic-worker consume task y procesa cada artifact
```

---

## 6.4 MinIO

Usado para almacenamiento de archivos.

Responsabilidad:

```txt
Guardar imágenes subidas o scrapeadas
Guardar PDFs subidos
Guardar texto extraído o recursos descargados
Guardar mapas ELA generados por cada artifact IMAGE
```

Ejemplo de rutas:

```txt
jobs/{job_id}/original.jpg
jobs/{job_id}/original.pdf
jobs/{job_id}/text_{artifact_id}.txt
jobs/{job_id}/img_{artifact_id}.jpg
jobs/{job_id}/ela_heatmap_{artifact_id}.png
```

---

## 7. Flujos funcionales

## 7.1 Flujo desde la landing sin iniciar sesión

Este flujo permite probar el sistema sin cuenta.

```txt
Usuario entra a la landing page
    ↓
Selecciona imagen, documento o URL
    ↓
Sube archivo o pega URL
    ↓
Frontend llama a Kong
    ↓
Kong redirige a forensic-api
    ↓
forensic-api crea un job demo con user_id = null
    ↓
Capa 1: forensic-api crea la lista de artifacts
    (1 artifact si es archivo directo; 1 TEXT + N IMAGE si es URL con página HTML)
    ↓
forensic-api guarda cada artifact en MinIO
    ↓
forensic-api guarda job PENDING (con su lista de artifacts) en MongoDB
    ↓
forensic-api encola tarea en Redis
    ↓
Capa 2: forensic-worker procesa cada artifact (en paralelo)
    ↓
Capa 3: forensic-worker consolida los resultados en un veredicto único
    ↓
forensic-worker guarda resultado consolidado en MongoDB
    ↓
Frontend consulta el estado del job
    ↓
Landing muestra resultado básico
```

Resultado público:

```txt
Probabilidad de autenticidad
Riesgo de manipulación
Veredicto general
Mensaje para iniciar sesión si desea ver más detalles
```

No se muestra:

```txt
Detalle técnico completo
Eventos internos
Scores parciales completos por artifact
Texto OCR completo
Flags técnicos completos
```

---

## 7.2 Flujo con usuario autenticado

Este flujo permite guardar historial y mostrar reportes completos.

```txt
Usuario inicia sesión
    ↓
auth-service valida credenciales
    ↓
auth-service retorna JWT
    ↓
Frontend guarda sesión
    ↓
Usuario entra al dashboard
    ↓
Sube imagen, documento o URL
    ↓
Frontend llama a forensic-api mediante Kong
    ↓
forensic-api valida JWT
    ↓
forensic-api crea job asociado al user_id
    ↓
Capa 1: forensic-api crea la lista de artifacts (igual que en el flujo demo)
    ↓
forensic-api guarda cada artifact en MinIO
    ↓
forensic-api guarda job PENDING en MongoDB
    ↓
forensic-api encola tarea en Redis
    ↓
Capa 2: forensic-worker procesa cada artifact (en paralelo)
    ↓
Capa 3: forensic-worker consolida los resultados
    ↓
forensic-worker guarda reporte detallado (por artifact + consolidado) en MongoDB
    ↓
Dashboard consulta resultado
    ↓
Usuario ve reporte completo
```

Reporte autenticado:

```txt
Fraud Score consolidado
Veredicto
Scores parciales por cada artifact (exif_score, ela_score, dct_benford_score, benford_score, etc.)
Flags detectados por DeepSeek y Gemini
Texto OCR si aplica
Mapa ELA por cada artifact IMAGE
Política de consolidación aplicada y artifact dominante
Eventos del job
Historial de análisis
```

---

## 8. Pipeline forense en 3 capas (modelo corregido)

El pipeline se ejecuta principalmente en `forensic-worker`, con la Capa 1 en `forensic-api`.

La regla vigente es:

```txt
Un job contiene una lista de artifacts.
Cada artifact se procesa por su rama correspondiente (TEXT o IMAGE).
La Capa 3 consolida todos los resultados en un veredicto único.
```

---

## 8.1 Capa 1 — Ingesta y Extracción (forensic-api)

Convierte la entrada del usuario en una lista de artifacts listos para analizar.

```txt
forensic-api recibe archivo o URL
    ↓
¿Qué tipo de entrada es?
    ├── Archivo imagen        → crea 1 artifact IMAGE
    ├── Archivo documento     → crea 1 artifact TEXT/DOCUMENT
    └── URL:
          ├── Apunta directo a una imagen  → crea 1 artifact IMAGE
          ├── Apunta directo a un PDF      → crea 1 artifact TEXT/DOCUMENT
          └── Apunta a una página HTML     → Scrapfly descarga el DOM
                  ├── Extrae texto limpio → crea 1 artifact TEXT
                  └── Extrae imágenes candidatas del DOM
                          → aplica filtro de relevancia
                          → crea 1 artifact IMAGE por cada candidata (máx. N)
    ↓
Todo se guarda en MinIO
    ↓
Job queda con la lista de artifacts, estado PENDING
    ↓
Se encola en Redis
```

### Filtro de relevancia de imágenes

Una página web puede traer decenas de imágenes irrelevantes (íconos, logos, banners). Enviar todas a Gemini es costoso e innecesario. Antes de crear artifacts `IMAGE` desde una URL, se aplica un filtro barato y determinista:

| Criterio | Regla |
|---|---|
| Dimensiones mínimas | Descartar imágenes menores a un umbral (ej. 200×200 px) — suelen ser íconos/logos |
| Deduplicación | Descartar imágenes con hash perceptual repetido (banners reutilizados) |
| Posición en el DOM | Priorizar imágenes dentro del contenido principal, no en header/footer/sidebar |
| Límite superior | Tomar como máximo N candidatas (ej. 5) para controlar costo y latencia |

Este filtro es una **regla de negocio**, no un detalle técnico: vive como servicio de dominio `ArtifactSelectionService`, no dentro del adaptador de Scrapfly.

---

## 8.2 Capa 2 — Análisis Cognitivo y Técnico (forensic-worker, por artifact, en paralelo)

Cada artifact se procesa de forma independiente y, cuando la infraestructura lo permite, en paralelo (ej. `asyncio.gather` en Python o tareas Celery hijas por artifact). Un artifact lento o fallido no debe bloquear a los demás; su resultado se marca `FAILED` a nivel de artifact sin tumbar el job completo.

```txt
Job con N artifacts
    ↓
Por cada artifact:
    ├── TEXT  → OCR (si el origen fue un documento/PDF escaneado)
    │              → DeepSeek: extraer JSON estructurado (document_type + montos + flags)
    │              → Evaluar aplicabilidad de Benford (ver sección 9)
    │
    └── IMAGE → EXIF   (metadatos, local, muy rápido)
                → ELA    (mapa de recompresión, local)
                → DCT    (coeficientes de compresión JPEG, local — evaluar aplicabilidad)
                → Gemini Vision (interpretación visual con IA, API externa)
```

Para cada artifact `IMAGE`, EXIF, ELA y DCT corren en paralelo entre sí (son análisis locales, deterministas, sin llamada a API externa) y terminan antes que Gemini Vision, que es la llamada más lenta por depender de una API externa. El tiempo total de la Capa 2 queda dominado por Gemini Vision y por el OCR de documentos largos, no por los análisis locales.

### EXIF básico

Extrae metadatos de la imagen. No es un cálculo, es lectura directa del archivo.

Puede detectar:

```txt
Software de edición
Fecha de captura sospechosa
Ausencia de metadatos
Modelo de cámara
```

**Tecnología:** `ExifTool` o `Pillow`. **Adaptador:** `ExifToolAdapter` / `PillowExifAdapter`, implementa `ExifAnalyzerPort`.

Es el análisis más liviano y rápido de todos — literalmente leer un header del archivo, sin cómputo pesado. Como señal aislada es la más débil de las tres locales: cualquiera puede borrar o falsificar metadatos con un editor.

---

### ELA (Error Level Analysis)

Recomprime la imagen a una calidad JPEG de referencia y compara la diferencia contra el original, píxel por píxel. Las zonas editadas después de la compresión original reaccionan distinto a esa recompresión — se ven como "manchas" más claras en el mapa resultante.

Puede ayudar a encontrar:

```txt
Zonas recomprimidas
Regiones editadas
Elementos pegados o alterados
```

**Tecnología:** `OpenCV`. **Adaptador:** `OpenCvElaAdapter`, implementa `ElaAnalyzerPort`. Genera un heatmap (`ela_heatmap_{artifact_id}.png`) que se guarda en MinIO. Su resultado se guarda como `ela_score` (0.0–1.0).

Es relativamente ligero si se aplica a imágenes de tamaño controlado. A diferencia de DCT, ELA no está restringido a JPEG — funciona en cualquier formato de imagen, aunque su fiabilidad es mayor sobre JPEG. No requiere una regla de aplicabilidad tan estricta como la de DCT/Benford.

---

### DCT (coeficientes de compresión JPEG)

Analiza los coeficientes matemáticos de la Transformada Discreta del Coseno (DCT), el algoritmo que usa JPEG internamente para comprimir. En la práctica, **el análisis DCT es la aplicación de la Ley de Benford a imágenes** (ver sección 9.3 para la regla completa de aplicabilidad).

Aplica principalmente a:

```txt
Imágenes JPEG (o cualquier formato con compresión con pérdida basada en DCT)
```

No debe aplicarse como señal fuerte en PNG o TIFF sin compresión JPEG — en esos casos se marca `benford_applicable: false` para ese artifact, en vez de forzar un resultado sin sentido.

**Tecnología:** `OpenCV` + `NumPy`/`SciPy`. **Adaptador:** `OpenCvDctAdapter`, implementa `DctAnalyzerPort`. Su resultado se guarda como `dct_benford_score`.

Es la señal local más robusta de las tres, porque no depende del contenido semántico de la imagen sino de un proceso matemático de compresión, difícil de falsificar sin dejar rastro.

---

### Gemini Vision

Modelo de visión/IA usado para detectar señales visuales de manipulación que EXIF/ELA/DCT no pueden capturar por sí solos, al "interpretar" la imagen completa en vez de calcular un patrón matemático.

Puede devolver flags como:

```txt
inconsistent_lighting
cloning_artifact
possible_editing
object_inconsistency
```

Para mantener el sistema ligero:

```txt
Se aplica solo sobre las imágenes que pasaron el filtro de relevancia (máx. N por job)
Se limita el tamaño de la imagen antes de enviar
Se usa solo en el worker, nunca en la request directa
```

**Tecnología:** Gemini API. **Adaptador:** `GeminiVisionAnalyzerAdapter`, implementa `ImageCognitiveAnalyzerPort`.

**Importante:** Gemini no reemplaza a EXIF/ELA/DCT. Estos últimos son cálculos deterministas y reproducibles (mismo input → mismo output, verificable), mientras que Gemini es un modelo probabilístico — puede ser inconsistente entre ejecuciones o interpretar de más. Por eso EXIF/ELA/DCT corren siempre como base técnica objetiva, y Gemini se usa como capa adicional de interpretación semántica, no como sustituto.

---

### OCR (para artifacts TEXT que provienen de documentos)

El OCR convierte el texto que aparece visualmente en un documento/PDF en texto plano que la máquina puede leer y analizar. Es obligatorio para documentos: sin OCR el sistema no puede leer el contenido, solo podría analizarlo visualmente.

Permite extraer:

```txt
Texto visible
Fechas
Montos
Nombres
Campos relevantes
```

**Tecnología:** `DeepSeek-OCR`, consumido vía API de terceros (DeepInfra), con endpoint compatible OpenAI: se envía la imagen del documento/página en base64 y se recibe el texto extraído. **Adaptador:** `DeepSeekOcrAdapter`, implementa `OcrPort`.

**Importante — es un modelo distinto al DeepSeek que clasifica el texto:** `DeepSeek-OCR` es un modelo de visión especializado solo en leer el contenido de una imagen y devolver texto plano. No clasifica `document_type`, no detecta montos ni flags — esa parte sigue haciéndola el DeepSeek de texto (`DeepSeekAnalyzerAdapter`, sección siguiente), que recibe como entrada el texto que ya extrajo `DeepSeek-OCR`. Son dos llamadas encadenadas:

```txt
Documento/PDF (convertido a imagen si hace falta)
    ↓
DeepSeek-OCR (vía DeepInfra) → extrae el texto crudo
    ↓
DeepSeek (API oficial) → document_type + financial_amounts + ai_flags
```

Se eligió la vía de API de terceros (DeepInfra) en vez de despliegue local porque `DeepSeek-OCR` requiere GPU NVIDIA con CUDA para correr con rendimiento aceptable, y el proyecto no cuenta con esa infraestructura dedicada — usar la API evita depender de una GPU propia, a costo de una llamada externa adicional y su latencia/costo asociados.

Para mantenerlo ligero:

```txt
Limitar el PDF a 1 o 2 páginas en el MVP
Reducir resolución de la imagen antes de enviarla a DeepSeek-OCR si es necesario
No ejecutar OCR sobre artifacts IMAGE que no son documentos
```

No aplica cuando el artifact TEXT proviene directamente de scraping HTML (ya viene como texto plano, sin necesidad de "leer" nada visualmente).

---

### DeepSeek (para artifacts TEXT)

Analiza el texto extraído (por OCR o por scraping) y lo clasifica semánticamente. Debe devolver un JSON estructurado:

```json
{
  "document_type": "FINANCIAL_INVOICE | RECEIPT | BANK_STATEMENT | CONTRACT | ARTICLE | PERSONAL_ID | GENERIC_TEXT",
  "financial_amounts": [1200.50, 340.00],
  "amount_count": 2,
  "ai_flags": ["template_like_wording", "urgency_language"]
}
```

Puede detectar:

```txt
Tipo de documento (clave: de aquí depende si se aplica Benford — ver sección 9)
Lenguaje sospechoso (urgencia, presión)
Contradicciones internas (fechas, nombres o cifras que no cuadran)
Texto genérico tipo plantilla
Montos financieros
```

**Tecnología:** DeepSeek API. **Adaptador:** `DeepSeekAnalyzerAdapter`, implementa `TextCognitiveAnalyzerPort`.

---

## 8.3 Capa 3 — Consolidación (forensic-worker)

Junta los resultados de todos los artifacts del job en un único veredicto.

```txt
Resultados por artifact (EXIF, ELA, DCT, Gemini, OCR, DeepSeek, Benford si aplica)
    ↓
ConsolidationService
    ↓
Política de consolidación:
    ├── worst_case_dominates (default) → fraud_score = el peor artifact manda
    └── weighted_average → promedio ponderado por tipo (caso específico, configurado explícitamente)
    ↓
Veredicto final + evento JOB_COMPLETED
```

`ConsolidationService` es lógica pura de **dominio**: no conoce Gemini, DeepSeek ni MongoDB. Solo recibe una lista de `PartialScoreDTO` (uno por artifact) y aplica la política configurada.

### Política de consolidación recomendada

Para un motor forense, se recomienda **"peor caso domina"**: si cualquier artifact del job resulta `REJECTED`, el job completo es `REJECTED`, sin importar cuántos otros artifacts estén limpios. Es más defendible que un promedio, porque en fraude un solo elemento manipulado ya compromete la validez del conjunto (ej. una sola foto de producto clonada en un anuncio con texto legítimo sigue siendo un anuncio fraudulento).

| Política | Cuándo usarla |
|---|---|
| `worst_case_dominates` | Por defecto. Un artifact de alto riesgo contamina el veredicto completo. |
| `weighted_average` | Casos específicos donde el negocio decide ponderar por tipo de artifact (ej. verificación de identidad → las fotos pesan más que el texto circundante). Debe quedar explícitamente configurado, no ser el default silencioso. |

---

## 9. Scoring y aplicabilidad de la Ley de Benford

El sistema calcula un `fraud_score` entre 0.0 y 1.0 (a nivel de artifact, y luego consolidado a nivel de job).

```txt
0.00 - 0.39 → APPROVED
0.40 - 0.74 → SUSPICIOUS
0.75 - 1.00 → REJECTED
```

### 9.1 Scores parciales posibles

Artifact IMAGE:

```txt
exif_score
ela_score
dct_benford_score
gemini_score
```

Artifact TEXT:

```txt
ocr_confidence (si vino de OCR)
deepseek_risk_score
benford_score (solo si aplica)
```

### 9.2 Reglas importantes

```txt
Cada score debe estar entre 0.0 y 1.0.
Si una señal no aplica, no se debe tratar como 0.0 (eso equivaldría a "aprobado, sin riesgo").
Los pesos deben renormalizarse excluyendo señales no aplicables para ese artifact específico.
El resultado público muestra solo porcentajes consolidados.
El resultado autenticado muestra el detalle técnico por artifact.
```

### 9.3 Por qué Benford no se aplica siempre (corrección v2)

La Ley de Benford solo es válida estadísticamente para conjuntos de números que:

- Surgen de un proceso natural/multiplicativo (montos financieros reales, poblaciones, mediciones que abarcan varios órdenes de magnitud).
- Tienen un tamaño de muestra suficiente (decenas de observaciones, no un puñado).

Se rompe con:

- Números asignados o secuenciales (IDs, números de factura consecutivos, teléfonos, códigos postales).
- Rangos artificialmente acotados (edades, porcentajes, calificaciones).
- Muestras pequeñas (3-10 números no permiten conclusión estadística).
- Textos sin naturaleza financiera (una cédula, un artículo de noticias, un contrato sin montos).

Aplicarla ciegamente genera falsos positivos y falsos negativos sin sentido.

### 9.4 Regla de aplicabilidad para artifacts TEXT

El prompt de DeepSeek clasifica el `document_type` además de extraer montos. El worker decide si ejecuta Benford según esta tabla:

| Condición | Acción |
|---|---|
| `document_type` es financiero (factura, recibo, estado de cuenta) **y** `amount_count` ≥ umbral mínimo (ej. 15–20) | Se aplica Benford sobre los montos |
| `document_type` es financiero pero `amount_count` insuficiente | `benford_applicable: false` — no se penaliza ni se favorece el score |
| `document_type` no es financiero (artículo, cédula, contrato sin montos, texto genérico) | No se aplica Benford. Se usan los flags de DeepSeek como señal alternativa |

Un resultado no aplicable **nunca** se traduce en `benford_score: 0`. Se representa como `benford_applicable: false`, y la fórmula de scoring ponderado **renormaliza los pesos excluyendo esa señal** para ese artifact específico.

### 9.5 Regla de aplicabilidad para artifacts IMAGE (DCT)

| Condición | Acción |
|---|---|
| Imagen en JPEG (o cualquier formato con compresión con pérdida basada en DCT) | Se aplica el análisis de coeficientes DCT |
| Imagen en formato sin pérdida (PNG, TIFF sin compresión JPEG) | `benford_applicable: false` para esa imagen — ELA y EXIF siguen aplicando igual |

### 9.6 Señal alternativa cuando Benford no aplica a un artifact TEXT

Cuando el artifact de texto no es financiero, no se deja el análisis vacío: se sustituye por la señal que ya produce el pipeline sin necesidad de infraestructura adicional — los **flags directos del prompt de DeepSeek** (lenguaje de urgencia/presión, contradicciones internas, redacción genérica tipo plantilla). No se usa memoria vectorial/ChromaDB para esto en el MVP (ver sección 3.2).

### 9.7 Tabla resumen de aplicabilidad

| Tipo de artifact | Condición | Señal usada |
|---|---|---|
| TEXT financiero, con suficientes montos | `document_type` financiero + `amount_count` ≥ umbral | Benford sobre montos |
| TEXT financiero, pocos montos | `document_type` financiero + `amount_count` < umbral | `benford_applicable: false`; se excluye del ponderado |
| TEXT no financiero | `document_type` ∉ {financieros} | Flags de DeepSeek; Benford no se ejecuta |
| IMAGE JPEG | Formato con compresión DCT | Análisis de coeficientes DCT + ELA + EXIF |
| IMAGE no-JPEG | Formato sin pérdida | `benford_applicable: false` (DCT); ELA y EXIF siguen aplicando |

---

## 10. Arquitectura hexagonal

La arquitectura hexagonal es obligatoria en el proyecto.

No reemplaza los microservicios. Se aplica dentro de cada microservicio.

```txt
Microservicios → dividen el sistema completo
Hexagonal → organiza internamente cada servicio
```

## 10.1 Servicios que deben usar arquitectura hexagonal

```txt
auth-service
forensic-api
forensic-worker
```

## 10.2 Servicios donde no aplica directamente

```txt
Kong API Gateway
Frontend Web
```

Kong es infraestructura. No contiene dominio de negocio.

El frontend puede usar arquitectura por features/componentes, pero no necesita hexagonal estricta.

## 10.3 Reglas de dependencia

```txt
Domain no depende de Application
Domain no depende de Infrastructure
Domain no importa frameworks
Domain no conoce MongoDB, Redis, MinIO, FastAPI, Celery o Spring
Application depende de Domain
Application define puertos
Infrastructure implementa puertos
Los controladores son adaptadores de entrada
Los repositorios, clientes externos y colas son adaptadores de salida
```

Dirección correcta:

```txt
Infrastructure → Application → Domain
```

Nunca:

```txt
Domain → Infrastructure
```

---

## 11. Domain Driven Design

DDD se aplicará para que el proyecto tenga un lenguaje de negocio claro y una estructura coherente.

## 11.1 Bounded Contexts

El sistema reducido tiene dos contextos principales.

### Identity Context

Ubicado en:

```txt
auth-service
```

Responsable de:

```txt
Usuario
Registro
Login
JWT
Sesión
```

No conoce detalles del análisis forense.

---

### Forensic Analysis Context

Ubicado en:

```txt
forensic-api
forensic-worker
```

Responsable de:

```txt
AnalysisJob
Artifact
Pipeline forense (3 capas)
Fraud Score
Veredicto
Eventos del job
Reporte
```

No maneja contraseñas ni registro de usuarios.

---

## 11.2 Lenguaje ubicuo

Estos términos deben usarse en código, documentación y conversaciones del equipo:

```txt
AnalysisJob
Artifact
ArtifactType
InputSource
FraudScore
Verdict
ForensicEvent
PartialScore
ConsolidatedResult
ConsolidationPolicy
DocumentType
BenfordApplicability
```

Evitar nombres genéricos como:

```txt
Data
Thing
Process
Object
ResponseInfo
FileData
```

---

## 11.3 Aggregate principal

El aggregate principal del contexto forense será:

```txt
AnalysisJob
```

Responsabilidades:

```txt
Controlar el estado del job y de cada artifact individual
Contener la lista de artifacts
Registrar eventos
Mantener el resultado consolidado
Impedir transiciones inválidas
```

Estados del job:

```txt
PENDING
PROCESSING
COMPLETED
FAILED
```

Reglas:

```txt
Un job PENDING puede pasar a PROCESSING.
Un job PROCESSING puede pasar a COMPLETED.
Un job PROCESSING puede pasar a FAILED.
Un job COMPLETED no debe volver a PROCESSING.
Un job FAILED puede registrar error, pero no debe generar reporte exitoso.
Un artifact individual puede marcarse FAILED sin tumbar el job completo,
siempre que al menos un artifact haya completado su análisis.
```

---

## 11.4 Entidades principales

```txt
User
AnalysisJob
Artifact
ConsolidatedResult
ForensicEvent
```

---

## 11.5 Value Objects

```txt
FraudScore
Verdict
ArtifactType
InputSource
DocumentType
BenfordApplicability
ConsolidationPolicy
```

Ejemplo de regla de value object:

```txt
FraudScore solo acepta valores entre 0.0 y 1.0.
```

---

## 11.6 Servicios de dominio

```txt
ArtifactSelectionService
BenfordApplicabilityService
FraudScoringService
ConsolidationService
```

### ArtifactSelectionService

Aplica el filtro de relevancia sobre las imágenes candidatas extraídas de una URL antes de crear los artifacts `IMAGE` (Capa 1). Descarta íconos/logos, duplicados y limita el número máximo de candidatas. Es una regla de negocio, por eso vive en `domain/`, no dentro del adaptador de scraping.

### BenfordApplicabilityService

Decide si Benford debe aplicarse a un artifact (TEXT según `document_type` + `amount_count`, o IMAGE según el formato de compresión). No ejecuta Benford. Solo decide si corresponde o no.

### FraudScoringService

Combina scores parciales y calcula el riesgo de un artifact individual.

### ConsolidationService

Con el modelo de artifacts múltiples, ya no es trivial:

```txt
fraud_score final = resultado de aplicar la política de consolidación
                     (worst_case_dominates por defecto) sobre la lista
                     de PartialScoreDTO de todos los artifacts del job
```

No conoce Gemini, DeepSeek ni MongoDB — solo recibe DTOs ya calculados y aplica la política configurada.

---

## 12. Puertos y adaptadores principales

## 12.1 auth-service

```txt
Puertos de entrada:
- RegisterUserUseCase
- LoginUserUseCase
- GetCurrentUserUseCase
- LogoutUserUseCase

Puertos de salida:
- UserRepositoryPort
- PasswordHasherPort
- TokenProviderPort
```

Adaptadores:

```txt
AuthControllerAdapter → Spring Web
JpaUserRepositoryAdapter → PostgreSQL
BCryptPasswordHasherAdapter → BCrypt
JwtTokenProviderAdapter → JWT
```

---

## 12.2 forensic-api

```txt
Puertos de entrada:
- SubmitDemoAnalysisUseCase
- SubmitAuthenticatedAnalysisUseCase
- GetJobStatusUseCase
- GetJobResultUseCase

Puertos de salida:
- JobRepositoryPort
- StoragePort
- TaskQueuePort
- UrlFetcherPort
- AuthTokenValidatorPort

Servicio de dominio (Capa 1):
- ArtifactSelectionService (filtro de relevancia de imágenes)
```

Adaptadores:

```txt
ForensicControllerAdapter → FastAPI
MongoJobRepositoryAdapter → MongoDB
MinioStorageAdapter → MinIO
CeleryTaskQueueAdapter → Redis/Celery
HttpUrlFetcherAdapter → HTTP client / Scrapfly (para scraping de DOM en URLs con HTML)
JwtValidatorAdapter → JWT
```

---

## 12.3 forensic-worker

```txt
Puerto de entrada:
- ProcessAnalysisJobUseCase

Puertos de salida:
- JobRepositoryPort
- StoragePort
- OcrPort
- TextCognitiveAnalyzerPort
- ImageCognitiveAnalyzerPort
- ExifAnalyzerPort
- ElaAnalyzerPort
- DctAnalyzerPort
- BenfordAnalyzerPort

Servicios de dominio (Capa 3):
- BenfordApplicabilityService
- FraudScoringService
- ConsolidationService
```

Adaptadores:

```txt
CeleryWorkerAdapter → Celery
MongoJobRepositoryAdapter → MongoDB
MinioStorageAdapter → MinIO
DeepSeekOcrAdapter → DeepSeek-OCR vía DeepInfra (implementa OcrPort)
DeepSeekAnalyzerAdapter → DeepSeek API (implementa TextCognitiveAnalyzerPort)
GeminiVisionAnalyzerAdapter → Gemini API (implementa ImageCognitiveAnalyzerPort)
ExifToolAdapter o PillowExifAdapter → EXIF
OpenCvElaAdapter → OpenCV (ELA)
OpenCvDctAdapter → OpenCV / NumPy (DCT)
BenfordStatisticalAdapter → NumPy / SciPy
```

---

## 13. Conexión completa del sistema

```txt
1. Usuario entra a la web.
2. Puede probar desde landing o iniciar sesión.
3. Si inicia sesión, auth-service genera JWT.
4. El usuario sube archivo o URL.
5. Frontend llama a Kong.
6. Kong enruta a forensic-api.
7. Capa 1: forensic-api crea el job y su lista de artifacts
   (1 artifact si es archivo directo; 1 TEXT + N IMAGE si es URL HTML,
   aplicando el filtro de relevancia antes de crear los artifacts IMAGE).
8. forensic-api guarda cada artifact en MinIO.
9. forensic-api guarda el job (con su lista de artifacts) en MongoDB.
10. forensic-api encola tarea en Redis.
11. forensic-worker toma la tarea.
12. Capa 2: forensic-worker descarga cada artifact desde MinIO y lo procesa
    en paralelo según su tipo (TEXT → OCR/DeepSeek; IMAGE → EXIF/ELA/DCT/Gemini).
13. Capa 3: forensic-worker aplica ConsolidationService sobre todos los
    scores parciales y calcula el fraud_score final según la política
    (worst_case_dominates por defecto).
14. forensic-worker guarda el resultado consolidado en MongoDB.
15. Frontend consulta estado y resultado.
16. Usuario ve resultado básico o detallado.
```

---

## 14. División sugerida del trabajo para 3 integrantes

## Integrante 1 — Frontend Web

Responsable de:

```txt
Landing page
Carga de imagen/documento/URL
Resultado público básico
Registro
Login
Dashboard autenticado
Vista de reporte detallado (por artifact + consolidado)
Consumo de API mediante Kong
Manejo de estados de carga y polling de job
```

Tecnologías:

```txt
React
Vite o Next.js
TypeScript
TailwindCSS
React Hook Form
Axios o Fetch
React Router si se usa Vite
```

Entregables de primera versión:

```txt
Pantalla landing con upload
Pantalla resultado básico
Pantalla login/register
Dashboard simple
Pantalla reporte detallado
```

---

## Integrante 2 — Plataforma e infraestructura

Responsable de:

```txt
auth-service
PostgreSQL
Kong API Gateway
Docker Compose
Configuración de variables de entorno
JWT
CORS
Rutas hacia servicios
Documentación de ejecución
```

Tecnologías:

```txt
Spring Boot
Spring Security
PostgreSQL
Kong
Docker
Docker Compose
JWT
BCrypt
```

Entregables de primera versión:

```txt
auth-service funcional
Endpoints register/login/me
Base de datos PostgreSQL
Kong enrutando a auth-service y forensic-api
Docker Compose base
```

---

## Integrante 3 — Motor forense

Responsable de:

```txt
forensic-api (Capa 1: ingesta, artifacts, filtro de relevancia)
forensic-worker (Capa 2: análisis por artifact; Capa 3: consolidación)
MongoDB
Redis
MinIO
Pipeline forense de 3 capas
OCR
EXIF
ELA
DCT
DeepSeek
Gemini Vision
Scoring y aplicabilidad de Benford
ConsolidationService
```

Tecnologías:

```txt
FastAPI
Celery
Redis
MongoDB
MinIO
OpenCV
DeepSeek-OCR (vía DeepInfra) para OCR
DeepSeek API (clasificación de texto)
Gemini API
NumPy / SciPy
Scrapfly (para scraping de URLs con HTML)
```

Entregables de primera versión:

```txt
Endpoint para crear análisis
Creación de jobs con lista de artifacts
Filtro de relevancia de imágenes
Cola Redis/Celery
Worker procesando artifacts en paralelo
Pipeline básico por tipo de artifact (TEXT / IMAGE)
ConsolidationService con política worst_case_dominates
Resultado consolidado guardado en MongoDB
Consulta de resultados
```

---

## 15. Prioridades para la primera versión

## Prioridad alta

```txt
Login y registro
Landing con upload
forensic-api creando jobs con su lista de artifacts
forensic-worker procesando artifacts en paralelo
ConsolidationService con política worst_case_dominates
MongoDB guardando resultados
Redis/Celery funcionando
Resultado básico visible
Resultado detallado para usuario autenticado
Docker Compose funcional
```

## Prioridad media

```txt
OCR básico
EXIF
ELA
DCT
Filtro de relevancia de imágenes (Capa 1)
Reglas de aplicabilidad de Benford (texto e imagen)
DeepSeek
Gemini Vision
Historial de análisis
Eventos dentro del job
```

## Prioridad baja o mejora futura

```txt
ChromaDB
Memoria vectorial (embeddings con Hugging Face: sentence-transformers / CLIP)
similarity_score
API keys
roles
admin dashboard
webhooks
C2PA
análisis avanzado de ruido
reportes PDF descargables
```

---

## 16. Conclusión

DeepForense MVP es una plataforma web con microservicios reducidos, orientada a analizar una o varias piezas de contenido (texto e imágenes) dentro de un mismo job, según lo que traiga la entrada del usuario: imagen, documento o URL.

La arquitectura final combina:

```txt
Microservicios
Arquitectura hexagonal
Domain Driven Design
Pipeline forense asíncrono en 3 capas (Ingesta → Análisis por artifact → Consolidación)
Procesamiento paralelo con worker
Resultados por Fraud Score consolidado
```

La corrección principal frente a la primera versión del proyecto no fue solo técnica, sino de **modelado del dominio**: pasar de "un job tiene un tipo" a "un job tiene artifacts, y el veredicto se consolida a partir de ellos" resuelve el problema de las URLs mixtas (texto + imágenes) y el de aplicar una técnica estadística (Benford) fuera de su contexto válido. Esta corrección se integró sin romper la arquitectura hexagonal ya definida: los servicios de dominio (`ArtifactSelectionService`, `BenfordApplicabilityService`, `ConsolidationService`) no dependen de ningún framework ni API externa, y los puertos de salida (DeepSeek, Gemini, EXIF, ELA, DCT, Benford) se implementan como adaptadores intercambiables.

La capa de memoria vectorial (ChromaDB + embeddings de Hugging Face) que se había considerado como señal adicional queda fuera de esta versión, consistente con la reducción de alcance del MVP — se mantiene como mejora futura.

La meta del equipo debe ser entregar primero un flujo completo de punta a punta:

```txt
Usuario sube archivo o URL
    ↓
Sistema crea job con su lista de artifacts
    ↓
Worker analiza cada artifact en paralelo
    ↓
Sistema consolida el resultado
    ↓
Frontend muestra veredicto
```

Una vez que este flujo funcione, se podrán agregar mejoras como API keys, auditoría independiente, ChromaDB, roles, panel administrativo y reportes avanzados.
