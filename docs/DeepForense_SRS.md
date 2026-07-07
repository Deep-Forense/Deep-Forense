# DeepForense — Especificación de Requerimientos de Software (SRS)

**Universidad Central del Ecuador — Facultad de Ingeniería en Sistemas de Información**
**Versión:** 1.0

---

## 1. Introducción

### 1.1 Propósito

Este documento especifica los requerimientos funcionales y no funcionales del sistema DeepForense, una plataforma web orientada a la detección de fraude y manipulación en contenido digital (imágenes, documentos y URLs). Sirve como referencia única entre los integrantes del equipo y la cátedra para entender **qué** debe hacer el sistema, independientemente de los detalles internos de implementación.

Complementa —no reemplaza— el documento de arquitectura técnica (`deepforense_mvp_consolidado.md`), donde se detalla el **cómo**: microservicios, patrones de diseño, modelo de dominio y pipeline de análisis.

### 1.2 Alcance del producto

DeepForense permite a cualquier persona subir una imagen, un documento PDF, o proporcionar una URL, y recibir un veredicto sobre la probabilidad de que ese contenido esté manipulado o sea fraudulento. El sistema calcula un puntaje de riesgo (Fraud Score) a partir de señales técnicas (metadatos, análisis de compresión, estadística) y señales de IA (interpretación visual y semántica), consolidando todo en un veredicto único por análisis.

Dos niveles de uso:
- **Demo pública** — sin cuenta, resultado resumido.
- **Modo autenticado** — con historial y reporte técnico detallado.

### 1.3 Definiciones y acrónimos

| Término | Definición |
|---|---|
| Job | Solicitud de análisis; agrupa uno o varios artifacts |
| Artifact | Unidad individual de contenido (texto o imagen) analizada de forma independiente |
| Fraud Score | Puntaje 0.0–1.0 que representa el riesgo de fraude/manipulación |
| Veredicto | APPROVED, SUSPICIOUS o REJECTED |
| EXIF | Metadatos técnicos embebidos en una imagen |
| ELA | Error Level Analysis — diferencias de recompresión |
| DCT | Discrete Cosine Transform — base matemática de la compresión JPEG |
| OCR | Conversión de texto visual a texto plano |
| Ley de Benford | Ley estadística sobre la distribución esperada del primer dígito |
| MVP | Minimum Viable Product |
| JWT | JSON Web Token |
| API Gateway | Punto único de entrada que enruta hacia los microservicios |

### 1.4 Referencias

- `deepforense_mvp_consolidado.md` (arquitectura técnica, pipeline de 3 capas, modelo de dominio)
- IEEE Std 830-1998 (estructura de referencia)

---

## 2. Descripción General

### 2.1 Perspectiva del producto

Producto nuevo, construido como microservicios independientes comunicados vía API Gateway. No se integra con sistemas legados. Se apoya en servicios externos de IA (DeepSeek, DeepSeek-OCR, Gemini) consumidos mediante adaptadores desacoplados del núcleo de negocio.

### 2.2 Funciones principales

- Recepción de contenido para análisis (imagen, documento o URL), con o sin autenticación
- Extracción de artifacts individuales a partir de la entrada (incluye URL con texto + imágenes)
- Ejecución de un pipeline técnico y de IA sobre cada artifact
- Consolidación de resultados parciales en un veredicto único por job
- Resultado básico (público) o detallado (autenticado)
- Gestión de cuentas e historial

### 2.3 Características de los usuarios

| Tipo de usuario | Descripción | Nivel técnico esperado |
|---|---|---|
| Usuario anónimo | Visitante que prueba el sistema sin registrarse | Ninguno |
| Usuario registrado | Analiza contenido de forma recurrente, lleva historial | Básico |
| Equipo de desarrollo | Mantiene y evoluciona el sistema | Avanzado |

### 2.4 Restricciones generales

- No hay GPU dedicada; cualquier modelo que la requiera se consume vía API externa
- PDF limitado a 1–2 páginas en el MVP
- Máximo N imágenes por job proveniente de una URL (por defecto 5)
- Dependencia de APIs de terceros (DeepSeek, Gemini, DeepInfra, Scrapfly); su caída puede degradar o impedir el análisis de artifacts que dependen de ellas

### 2.5 Supuestos y dependencias

- Acceso continuo a internet desde el entorno de despliegue
- Credenciales/API keys gestionadas de forma segura vía variables de entorno
- El volumen de uso académico no exige alta disponibilidad ni autoescalado

---

## 3. Requerimientos Específicos

### 3.1 Requerimientos Funcionales

| Código | Nombre | Descripción | Prioridad |
|---|---|---|---|
| RF-01 | Registro de usuario | Crear cuenta con nombre, correo y contraseña | Alta |
| RF-02 | Inicio de sesión | Autenticar credenciales y emitir JWT | Alta |
| RF-03 | Cierre de sesión | Invalidar la sesión activa | Media |
| RF-04 | Consulta de usuario actual | Endpoint `/me` con datos del usuario autenticado | Media |
| RF-05 | Análisis demo (sin autenticación) | Subir archivo o pegar URL sin iniciar sesión | Alta |
| RF-06 | Análisis autenticado | Enviar contenido y asociarlo al historial del usuario | Alta |
| RF-07 | Recepción de imagen | Aceptar JPG/PNG como entrada | Alta |
| RF-08 | Recepción de documento | Aceptar PDF como entrada | Alta |
| RF-09 | Recepción de URL | Determinar si la URL apunta a imagen, PDF o HTML | Alta |
| RF-10 | Creación de job con artifacts | Job con lista de artifacts según tipo de entrada | Alta |
| RF-11 | Extracción desde URL HTML | Extraer texto principal e imágenes candidatas del DOM | Alta |
| RF-12 | Filtro de relevancia de imágenes | Descartar íconos/banners/duplicados, límite máximo por job | Alta |
| RF-13 | Almacenamiento de artifacts | Guardar contenido de cada artifact en almacenamiento de objetos | Alta |
| RF-14 | Encolado de tareas | Encolar el job para procesamiento asíncrono | Alta |
| RF-15 | OCR de documentos | Extraer texto visible de un documento/PDF | Alta |
| RF-16 | Clasificación semántica de texto | Tipo de documento, montos, lenguaje sospechoso | Alta |
| RF-17 | Análisis de metadatos (EXIF) | Leer metadatos de cada artifact IMAGE | Alta |
| RF-18 | Análisis de recompresión (ELA) | Mapa de diferencias de recompresión | Alta |
| RF-19 | Análisis de coeficientes (DCT) | Coeficientes DCT en artifacts JPEG | Alta |
| RF-20 | Análisis visual con IA | Detectar anomalías visuales por modelo de visión | Alta |
| RF-21 | Aplicabilidad de Benford | Determinar si Benford aplica antes de usarlo como señal | Alta |
| RF-22 | Score parcial por artifact | Puntaje de riesgo 0.0–1.0 por artifact | Alta |
| RF-23 | Consolidación de resultados | Combinar scores parciales según política configurable | Alta |
| RF-24 | Veredicto final | APPROVED / SUSPICIOUS / REJECTED desde el Fraud Score | Alta |
| RF-25 | Consulta de estado del job | PENDING / PROCESSING / COMPLETED / FAILED | Alta |
| RF-26 | Resultado básico | Veredicto y porcentajes para usuarios no autenticados | Alta |
| RF-27 | Resultado detallado | Detalle técnico completo por artifact para autenticados | Alta |
| RF-28 | Registro de eventos del job | Eventos del ciclo de vida (creación, fin, fallos) | Media |
| RF-29 | Historial de análisis | Listado de análisis previos del usuario | Media |
| RF-30 | Enrutamiento centralizado | Un único punto de entrada (API Gateway) | Alta |

### 3.2 Requerimientos No Funcionales

| Código | Categoría | Descripción |
|---|---|---|
| RNF-01 | Arquitectura | Microservicios independientes, desplegables por separado |
| RNF-02 | Diseño interno | Arquitectura hexagonal por microservicio de negocio |
| RNF-03 | Modelado del dominio | DDD: agregados, entidades, value objects, servicios de dominio |
| RNF-04 | Procesamiento asíncrono | El análisis no bloquea la respuesta de la API |
| RNF-05 | Procesamiento paralelo | Artifacts de un mismo job procesables en paralelo |
| RNF-06 | Tolerancia a fallos parciales | Un artifact fallido no detiene el job completo |
| RNF-07 | Contenerización | Todos los servicios levantables con Docker Compose |
| RNF-08 | Seguridad de acceso | Contraseñas con BCrypt, sesiones con JWT |
| RNF-09 | CORS | Gestionado centralmente por el API Gateway |
| RNF-10 | Límites de recursos | Páginas de PDF y número de imágenes acotados |
| RNF-11 | Auditabilidad | Señales deterministas (EXIF/ELA/DCT) reproducibles y diferenciadas de señales de IA |
| RNF-12 | Dependencia de servicios externos | APIs de IA y scraping aisladas mediante puertos/adaptadores |
| RNF-13 | Usabilidad | Análisis básico completable en máx. 3 pasos sin cuenta |
| RNF-14 | Extensibilidad futura | El diseño no bloquea agregar roles, auditoría o memoria vectorial después |

---

## 4. Actores y Casos de Uso

### 4.1 Actores del sistema

| Actor | Descripción |
|---|---|
| Usuario anónimo | Visitante que usa la demo pública |
| Usuario registrado | Cuenta activa, historial y reportes detallados |
| Sistema (forensic-worker) | Actor no humano que ejecuta el análisis de forma autónoma |
| Administrador | Fuera del alcance del MVP — actor futuro |

### 4.2 Casos de uso principales

| Código | Nombre | Actor principal | Descripción |
|---|---|---|---|
| UC-01 | Registrarse | Usuario anónimo | Crear cuenta nueva |
| UC-02 | Iniciar sesión | Usuario registrado | Obtener token de sesión |
| UC-03 | Analizar contenido (demo) | Usuario anónimo | Subir/pegar URL, resultado básico sin login |
| UC-04 | Analizar contenido (autenticado) | Usuario registrado | Enviar contenido, ver reporte completo |
| UC-05 | Consultar historial | Usuario registrado | Revisar análisis anteriores |
| UC-06 | Procesar job de análisis | Sistema (worker) | Ejecutar pipeline 3 capas y consolidar veredicto |

#### UC-03 — Analizar contenido (demo)

```txt
1. El usuario anónimo ingresa a la landing page.
2. Selecciona subir una imagen/documento o pegar una URL.
3. El sistema crea un job con user_id nulo y extrae la lista de artifacts.
4. El sistema procesa el job de forma asíncrona.
5. El sistema muestra un resultado resumido: veredicto y porcentajes.
```
Flujo alternativo: entrada inválida (formato no soportado, URL inaccesible) → el sistema informa el error sin crear un job.

#### UC-04 — Analizar contenido (autenticado)

```txt
1. El usuario inicia sesión y obtiene un token válido.
2. Envía contenido a análisis desde el dashboard.
3. El sistema asocia el job al usuario autenticado.
4. Tras completarse, el usuario accede al reporte técnico completo por artifact
   y al resultado consolidado.
```

#### UC-06 — Procesar job de análisis (actor: Sistema)

```txt
1. El worker toma un job pendiente de la cola.
2. Descarga cada artifact desde el almacenamiento de objetos.
3. Ejecuta el pipeline correspondiente a cada tipo de artifact, en paralelo.
4. Marca como fallido cualquier artifact que no pudo completarse, sin detener
   el resto del job.
5. Consolida los resultados parciales aplicando la política de consolidación.
6. Guarda el resultado final y marca el job como completado.
```

---

## 5. Modelo de Datos Preliminar

### 5.1 Entidades principales

| Entidad | Almacén | Descripción |
|---|---|---|
| Usuario | PostgreSQL | Cuenta de acceso: nombre, correo, contraseña (hash) |
| AnalysisJob | MongoDB | Agrupa artifacts, estado, resultado consolidado y eventos |
| Artifact | MongoDB (embebido) | Unidad de contenido individual con su propio resultado |
| Archivo/Contenido crudo | MinIO | Bytes originales, imágenes scrapeadas, mapas ELA |

### 5.2 Estados del ciclo de vida de un job

```txt
PENDING     → job creado, en espera de procesamiento
PROCESSING  → artifacts en análisis
COMPLETED   → resultado consolidado disponible
FAILED      → el job no pudo completarse
```

---

## 6. Fuera del Alcance del MVP

Consideradas en etapas tempranas, excluidas explícitamente de esta versión, documentadas como mejoras futuras:

- Gestión de roles y permisos
- Panel administrativo
- Recuperación y cambio de contraseña
- API keys para integraciones de terceros
- Servicio de auditoría independiente
- Memoria vectorial (embeddings con Hugging Face y ChromaDB) para contenido reciclado
- Webhooks y notificaciones a sistemas externos
- Planes de suscripción o niveles empresariales
- Certificación de procedencia de contenido (C2PA)
- Análisis avanzado de ruido de sensor de cámara

La inclusión de cualquiera de estos elementos en una fase posterior debe acompañarse de una actualización formal de este documento.
