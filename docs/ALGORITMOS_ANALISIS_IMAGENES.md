# Algoritmos utilizados en el análisis de imágenes

## 1. Objetivo y mapa de implementación

El pipeline combina algoritmos deterministas con un modelo multimodal. Ningún algoritmo individual decide el veredicto: cada uno produce una señal, y el dominio las combina posteriormente.

| Algoritmo | Implementación | Entrada | Salida principal |
|---|---|---|---|
| Validación por firmas binarias | `forensic-api/.../rest/analysis_controller.py::_resolve_and_validate_artifact` | Bytes | Tipo `IMAGE` o error |
| Inspección EXIF | `pillow_exif_adapter.py::PillowExifAdapter` | Bytes | `exif_score` `[0,1]` |
| Error Level Analysis | `opencv_ela_adapter.py::OpenCvElaAdapter` | Bytes | `ela_score` y heatmap PNG |
| DCT por bloques | `opencv_dct_adapter.py::OpenCvDctAdapter` | JPEG | Coeficientes AC |
| Ley de Benford | `benford_statistical_adapter.py::BenfordStatisticalAdapter` | Coeficientes | `dct_benford_score` `[0,1]` |
| Inferencia visual | `gemini_vision_analyzer_adapter.py::GeminiVisionAnalyzerAdapter` | Imagen | Flags visuales confirmadas |
| Clasificación explicable | `image_classification_service.py::ImageClassificationService` | Flags, EXIF, ELA | Clasificación y mensaje |
| Scoring | `fraud_scoring_service.py::FraudScoringService` | `ArtifactAnalysis` | Riesgo por imagen |
| Consolidación | `consolidation_service.py::ConsolidationService` | Artefactos puntuados | Veredicto global |

El orquestador está en `ProcessAnalysisJobUseCase._analyze_image()`. Las clases de infraestructura implementan puertos definidos en `domain/ports`, de modo que el caso de uso no depende directamente de Pillow, OpenCV o APIs externas.

## 2. Validación por magic bytes

### Fundamento

La extensión y el MIME enviados por el navegador pueden falsificarse. Una firma binaria identifica el contenedor a partir de sus primeros bytes.

### Implementación

```text
si bytes empiezan FF D8 FF                 → JPEG
si bytes empiezan 89 50 4E 47 0D 0A 1A 0A → PNG
si empiezan RIFF y bytes[8:12] = WEBP      → WEBP
en otro caso                                → rechazar
```

El controlador también exige contenido no vacío y máximo 50 MiB. Para URL, `SubmitUrlAnalysisUseCase` vuelve a comprobar la firma y `PillowImageInspectorAdapter` intenta decodificar la imagen.

### Uso en el código

La validación determina `artifact_type="IMAGE"`. `SubmitAnalysisUseCase` guarda los bytes en MinIO, crea el agregado `AnalysisJob`, persiste en MongoDB y encola el identificador en Celery.

### Limitación

Una firma válida identifica el formato, no garantiza que todo el archivo sea íntegro. La apertura con Pillow añade una segunda defensa para URL; el archivo subido será decodificado más tarde por los analizadores.

## 3. Algoritmo EXIF

### Fundamento

EXIF es un conjunto de metadatos incrustado en algunas imágenes. El software creador y las fechas pueden indicar edición, pero son señales débiles porque los metadatos pueden eliminarse o modificarse.

### Implementación

`PillowExifAdapter._analyze_sync()` abre un `BytesIO` mediante Pillow y consulta:

- tag `0x0131`: `Software`;
- tag `0x0132`: `DateTime`;
- IFD `0x8769`, tag `0x9003`: `DateTimeOriginal`.

Pseudocódigo:

```text
score = 0
si Software contiene editor conocido:           score += 0.45
si DateTime != DateTimeOriginal:                 score += 0.35
si existe DateTime pero no DateTimeOriginal:     score += 0.15
devolver min(1, score)
```

Editores buscados: Photoshop, GIMP, Lightroom, Affinity, Pixelmator, Canva, Paint.NET, Photopea, Snapseed y Picsart.

Si no hay EXIF devuelve `0.0`; la ausencia no se considera fraude. El método async usa `asyncio.to_thread()` porque Pillow realiza trabajo bloqueante.

### Cómo se usa

`_analyze_image()` asigna el valor a `ArtifactAnalysis.exif_score`. El scoring lo incluye en el promedio técnico. También ayuda a clasificar `AUTHENTIC`: debe ser `≤0.20`, además de cumplirse las condiciones de ELA y Gemini.

### Limitaciones

- Los metadatos pueden borrarse sin editar píxeles.
- Un editor legítimo activa la heurística.
- No verifica cámara, firma criptográfica ni cadena de custodia.

## 4. Error Level Analysis (ELA)

### Fundamento

JPEG comprime con pérdida. Cuando una región pasó por una historia de compresión distinta, su error al volver a comprimir puede diferir del resto. ELA compara la imagen decodificada con una recompresión homogénea.

### Implementación matemática

OpenCV decodifica en BGR y vuelve a codificar a JPEG con calidad 90:

```text
D(x,y,c) = |I_original(x,y,c) - I_recomprimida(x,y,c)|
mean_diff = promedio de D para todos los píxeles y canales
ela_score = min(1, mean_diff / 25)
```

El score se redondea a cuatro decimales. Una diferencia media de 25 o superior satura en 1.

### Heatmap

Para visualizar:

```text
gray_diff(x,y) = promedio de D en los 3 canales
peak = percentil 99 de gray_diff
normalized = clip(gray_diff / peak × 255, 0, 255)
heatmap = colormap JET(normalized)
```

El percentil 99 evita que un único píxel extremo reduzca el contraste del resto. Esta normalización solo afecta la imagen visual; no modifica `ela_score`.

### Uso en el código

`OpenCvElaAdapter.analyze()` ejecuta `_analyze_sync()` en un thread. `_analyze_image()` guarda el heatmap en MinIO y registra `ela_score` y `ela_heatmap_ref`. La API convierte la referencia interna en una URL protegida para el propietario.

### Coste y limitaciones

El coste es aproximadamente O(ancho × alto) y requiere mantener matrices de la imagen en memoria. ELA puede reaccionar a recompresión normal, ruido o formato; una composición aplanada uniformemente puede no dejar una región diferencial.

## 5. Transformada Discreta del Coseno (DCT)

### Fundamento

JPEG representa bloques 8×8 mediante frecuencias DCT. El coeficiente DC representa el promedio del bloque; los 63 coeficientes AC representan variaciones espaciales. Su distribución puede cambiar con edición y recompresión.

Para un bloque `f(x,y)`, conceptualmente:

```text
F(u,v) = α(u)α(v) Σx Σy f(x,y)
         cos((2x+1)uπ/16) cos((2y+1)vπ/16)
```

### Implementación

`OpenCvDctAdapter`:

1. Decodifica en escala de grises.
2. Toma un recorte central máximo de 512×512.
3. Ajusta dimensiones a múltiplos de 8.
4. Reorganiza la matriz en bloques 8×8.
5. Ejecuta `cv2.dct()` por bloque.
6. Descarta el índice 0, coeficiente DC.
7. Usa valor absoluto de AC y descarta valores `≤1e-6`.

Se rechazan imágenes menores de 8×8. El recorte limita CPU/memoria y crea una muestra estable, aunque puede omitir una edición situada en los bordes.

### Aplicabilidad

`BenfordApplicabilityService.applies_to_image()` lo habilita únicamente si los bytes empiezan con la firma JPEG. En PNG y WEBP no se ejecuta y el campo queda `null`.

## 6. Ley de Benford sobre DCT

### Fundamento

Benford predice que, en ciertas series naturales, el primer dígito no es uniforme:

```text
P(d) = log10(1 + 1/d), d ∈ {1,...,9}
```

El dígito 1 aparece aproximadamente 30,1%, mientras el 9 aparece cerca de 4,6%. El sistema compara los primeros dígitos de los coeficientes DCT AC con esa distribución.

### Implementación

`_first_significant_digit()` escala el valor absoluto hasta `[1,10)` y toma el entero. Se excluyen cero, NaN e infinito. Debe haber al menos cinco dígitos útiles.

```text
TV = 0.5 × Σd |P_observada(d) - P_Benford(d)|
dct_benford_score = min(1, TV / 0.30)
```

La distancia de variación total `TV` está en `[0,1]`. El factor 0.30 hace que una desviación de 0.30 ya represente riesgo máximo.

### Uso

`_analyze_image()` encadena `extract_coefficients()` y `BenfordStatisticalAdapter.score()`. El resultado entra en `ArtifactAnalysis.dct_benford_score` y en el promedio técnico.

### Limitaciones

Benford es una heurística estadística, no un detector universal. Contenido, cámara, edición legítima, tamaño o compresión repetida influyen en la distribución.

## 7. Inferencia visual con Gemini

### Naturaleza del método

No es un algoritmo determinista local. Es una inferencia mediante un modelo multimodal remoto. El código restringe su comportamiento con prompt conservador, esquema JSON, temperatura 0 y verificación secundaria.

### Implementación

`GeminiVisionAnalyzerAdapter._request_findings()`:

1. Detecta MIME por firma.
2. Codifica bytes en Base64.
3. Envía imagen y prompt a `generateContent`.
4. Exige objetos `{flag, confidence, evidence}` bajo un schema cerrado.
5. Conserva únicamente confianza `HIGH` con evidencia no vacía.

Flags admitidas:

- generación: `ai_generation_artifacts`, `synthetic_texture`, `anatomical_inconsistency`;
- edición IA: `ai_inpainting_artifacts`, `generative_fill_artifacts`;
- edición tradicional: `cloned_region`, `compositing_artifacts`, `inconsistent_lighting`, `warped_text`;
- captura: `screenshot_ui_elements`, `screen_capture_artifacts`.

Las cinco primeras son críticas. Si aparecen, `analyze()` hace una segunda petición que intenta refutarlas. Solo conserva la intersección de hallazgos HIGH de ambas evaluaciones.

Las solicitudes usan `post_with_retry()`, timeout de 90 segundos y reintentos para condiciones transitorias definidas por el adaptador HTTP.

### Fallos

El caso de uso captura errores de Gemini. En ese caso:

```text
gemini_flags = []
image_classification = INCONCLUSIVE
cognitive_available = false
analysis_warnings = [cognitive_analysis_unavailable]
```

EXIF, ELA y DCT se conservan.

## 8. Algoritmo de clasificación visual

`classification_from_flags()` aplica prioridad:

```text
generación IA > modificación IA > screenshot > edición > sin clasificación
```

Si no existen flags:

```text
si exif_score ≤ 0.20 y ela_score < 0.15 → AUTHENTIC
en otro caso                               → INCONCLUSIVE
```

La salida incluye `image_classification_message`. Esta clasificación describe el tipo de evidencia; no es el veredicto matemático del job.

## 9. Algoritmo de scoring

`ArtifactAnalysis.numeric_scores()` retorna las señales presentes. Para una imagen son EXIF, ELA y DCT/Benford si aplica.

```text
flags = unión deduplicada de ai_flags y gemini_flags
flags_factor = min(1, |flags| / 3)
signal_mean = media de señales numéricas presentes
combined = 0.70 × signal_mean + 0.30 × flags_factor
fraud_score = clip(max(combined, semantic_floor), 0, 1)
```

Pisos: generación IA `0.75`, modificación IA `0.75`, edición `0.40`. Screenshot no tiene piso. El score se redondea a cuatro decimales.

Es importante que las flags estén duplicadas en `ai_flags` y `gemini_flags` para compatibilidad de contrato: el uso de conjuntos impide contarlas dos veces.

## 10. Consolidación

El caso de uso crea un `ScoredArtifact`. `analysis_complete` es falso si el análisis cognitivo falló. La política por defecto toma el artefacto de mayor riesgo. La alternativa calcula promedio ponderado por tipo, imagen 0.70 y texto 0.30.

```text
score < 0.40       → APPROVED
0.40 ≤ score ≤0.70 → SUSPICIOUS
score > 0.70       → REJECTED
```

Si falta análisis cognitivo y el resultado normal sería APPROVED, se convierte en `INCONCLUSIVE`. Los porcentajes son riesgo `round(score×100)` y autenticidad `round((1-score)×100)`, salvo autenticidad nula en inconcluso.

## 11. Ensamblaje e inyección

`app/worker.py::build_process_job_use_case()` construye:

```text
PillowExifAdapter
OpenCvElaAdapter
OpenCvDctAdapter
BenfordStatisticalAdapter
GeminiVisionAnalyzerAdapter
ImageClassificationService
FraudScoringService
ConsolidationService
```

Los parámetros provienen del entorno, particularmente `GEMINI_API_KEY`, `GEMINI_MODEL` y `CONSOLIDATION_POLICY`. Celery invoca `process_analysis_job()`, que crea el caso de uso y ejecuta `asyncio.run(use_case.execute(job_id))`.

## 12. Pruebas asociadas

- `test_pillow_exif_adapter.py`;
- `test_opencv_ela_adapter.py`;
- `test_dct_benford_adapters.py`;
- `test_gemini_vision_analyzer_adapter.py`;
- `test_image_classification_service.py`;
- `test_fraud_scoring_service.py`;
- `test_consolidation_service.py`;
- `test_process_analysis_job_use_case.py`.

Estas pruebas permiten cambiar un algoritmo conservando el puerto y verificando independientemente la regla de dominio.
