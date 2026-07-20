# Flujo completo de análisis de imágenes

## 1. Alcance

Este documento describe el comportamiento implementado cuando DeepForense recibe una imagen:

- subida como archivo JPEG, PNG o WEBP;
- enviada mediante una URL pública directa a una imagen JPEG, PNG o WEBP.

Ambas entradas terminan en el mismo pipeline forense. La diferencia está únicamente en la adquisición y en el campo `origin`: `UPLOAD` para archivo y `DIRECT_URL` para URL.

> Un resultado `AUTHENTIC` o `APPROVED` significa que no se encontraron señales suficientes con las comprobaciones disponibles. No demuestra de forma absoluta que la imagen sea original.

## 2. Entrada por archivo

### 2.1 Solicitud

- Demo: `POST /api/forensic/demo/analyze`.
- Autenticado: `POST /api/forensic/analyze` con JWT.
- Content-Type: `multipart/form-data`.
- Campo: `file`.
- No se puede enviar simultáneamente `file` y `url`.

### 2.2 Validaciones

La API lee los bytes reales; no confía en la extensión ni en el MIME declarado.

| Validación | Condición | Resultado si falla |
|---|---|---|
| Contenido | Debe contener al menos 1 byte | HTTP 400 |
| Tamaño | Máximo `50 × 1024 × 1024` bytes = 50 MiB | HTTP 413 |
| JPEG | Empieza con `FF D8 FF` | Aceptado como `IMAGE` |
| PNG | Empieza con la firma PNG completa | Aceptado como `IMAGE` |
| WEBP | Contenedor `RIFF` y bytes 8–11 iguales a `WEBP` | Aceptado como `IMAGE` |
| Otro formato | GIF, TIFF, BMP, SVG, etc. | HTTP 400 |

La imagen se guarda en MinIO como `uploads/{uuid}-{nombre_original}`. Después se crea en MongoDB un job con estado `PENDING` y un artefacto `IMAGE`, y se publica en Redis la tarea `process_analysis_job(job_id)`.

Respuesta HTTP 202:

```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "artifacts_count": 1
}
```

## 3. Entrada por URL

### 3.1 Solicitud

Se usan los mismos endpoints, enviando el campo de formulario `url` en vez de `file`.

### 3.2 Descarga y seguridad

| Regla | Valor implementado |
|---|---|
| Esquemas | Solo `http` y `https` |
| URL | Debe tener hostname |
| Destinos explícitamente bloqueados | `localhost`, subdominios `.localhost` e IP no global |
| Redirecciones | Máximo 5; cada destino se vuelve a validar |
| Timeout HTTP | 30 segundos |
| Tamaño | Máximo 50 MiB, comprobado en `Content-Length` y durante streaming |
| Contenido final | Debe ser JPEG, PNG o WEBP por magic bytes y abrir correctamente con Pillow |

No se analiza una página HTML ni se extraen imágenes de una web. La URL debe apuntar directamente al archivo de imagen. El nombre se toma del último segmento de la URL y el artefacto se guarda con `origin=\"DIRECT_URL\"`.

Después de la descarga, almacenamiento y creación del job, el procesamiento es idéntico al de una imagen subida como archivo.

## 4. Procesamiento asíncrono

```text
Imagen archivo/URL
       │
       ▼
Validación → MinIO → Job PENDING en Mongo → Redis/Celery
                                                │
                                                ▼
                                          Job PROCESSING
                                                │
              ┌─────────────────────────────────┼──────────────────────────────┐
              ▼                                 ▼                              ▼
         EXIF/Pillow                       ELA/OpenCV                  Gemini visual
                                                │
                                                └──────── DCT + Benford (solo JPEG)
                                                                    │
                                                                    ▼
                                                    Score por artefacto + veredicto
```

El worker descarga la imagen desde MinIO. EXIF, ELA y DCT son análisis técnicos; Gemini es un análisis cognitivo externo. Si el análisis técnico lanza una excepción, el artefacto falla. Si solo falla Gemini, se conservan EXIF/ELA/DCT y el resultado se marca incompleto.

## 5. Señal EXIF

Pillow lee los metadatos EXIF. El valor `exif_score` está entre 0 y 1 y se calcula sumando:

| Evidencia | Aporte de riesgo |
|---|---:|
| `Software` contiene Photoshop, GIMP, Lightroom, Affinity, Pixelmator, Canva, Paint.NET, Photopea, Snapseed o Picsart | `+0.45` |
| `DateTime` y `DateTimeOriginal` existen pero son diferentes | `+0.35` |
| Existe `DateTime` pero falta `DateTimeOriginal` | `+0.15` |

El resultado se limita a 1. Una imagen sin EXIF recibe `0.0`, porque perder metadatos es habitual y no constituye fraude por sí solo.

Ejemplos:

- Photoshop + fechas distintas: `0.45 + 0.35 = 0.80`.
- Solo fecha original eliminada: `0.15`.
- Sin EXIF: `0.00`.

## 6. Señal ELA

Error Level Analysis recomprime la imagen como JPEG con calidad 90 y calcula por píxel la diferencia absoluta con la imagen decodificada original.

```text
mean_diff = promedio de las diferencias absolutas de todos los canales
ela_score = min(1, mean_diff / 25)
```

Interpretación aproximada definida por el código:

- `mean_diff=0` produce `ela_score=0`;
- `mean_diff=5` produce `0.20`;
- `mean_diff=12.5` produce `0.50`;
- `mean_diff≥25` produce `1.00`.

Además se genera un heatmap PNG. Su contraste se normaliza con el percentil 99 de esa imagen y se colorea con JET. Esta normalización sirve para visualizar diferencias relativas; no cambia `ela_score`. El heatmap se almacena en:

```text
jobs/{job_id}/artifacts/{artifact_id}/ela_heatmap.png
```

El propietario autenticado puede obtenerlo en `GET /api/forensic/jobs/{job_id}/artifacts/{artifact_id}/ela-heatmap`.

ELA puede señalar recompresión o regiones diferentes, pero no prueba por sí solo una edición maliciosa.

## 7. DCT y Ley de Benford

Solo se ejecuta para JPEG. En PNG y WEBP:

```json
{"benford_applicable": false, "dct_benford_score": null}
```

Para JPEG:

1. Convierte la imagen a escala de grises.
2. Recorta una zona central de máximo 512×512 píxeles.
3. Divide en bloques de 8×8.
4. Calcula DCT y descarta el coeficiente DC de cada bloque.
5. Conserva coeficientes AC absolutos mayores que `1e-6`.
6. Obtiene el primer dígito significativo y lo compara con Benford.

La distribución teórica es `P(d)=log10(1+1/d)`. La distancia usada es:

```text
TV = 0.5 × Σ |frecuencia_observada(d) - frecuencia_Benford(d)|
dct_benford_score = min(1, TV / 0.30)
```

Se requieren al menos 5 valores útiles. Ejemplos: `TV=0.03 → 0.10`, `TV=0.15 → 0.50`, `TV≥0.30 → 1.00`. Un valor mayor significa mayor desviación respecto a Benford.

## 8. Análisis visual con Gemini

La imagen se envía al modelo configurado por `GEMINI_MODEL`. La petición usa temperatura 0, seed 42 y salida JSON estructurada. Solo se aceptan hallazgos con confianza `HIGH` y evidencia textual no vacía.

### 8.1 Flags posibles

| Grupo | Flags | Clasificación |
|---|---|---|
| Generación IA | `ai_generation_artifacts`, `synthetic_texture`, `anatomical_inconsistency` | `AI_GENERATED` |
| Modificación IA | `ai_inpainting_artifacts`, `generative_fill_artifacts` | `AI_MODIFIED` |
| Captura | `screenshot_ui_elements`, `screen_capture_artifacts` | `SCREENSHOT` |
| Edición | `cloned_region`, `compositing_artifacts`, `inconsistent_lighting`, `warped_text` | `EDITED` |

Las cinco flags de generación/modificación por IA son críticas. Si aparecen, el sistema hace una segunda consulta independiente y escéptica; una flag solo se conserva cuando ambas respuestas coinciden en `HIGH`.

### 8.2 Clasificación visual

Se evalúa en este orden:

1. Alguna flag de generación: `AI_GENERATED`.
2. Alguna flag de modificación IA: `AI_MODIFIED`.
3. Alguna flag de captura: `SCREENSHOT`.
4. Alguna flag de edición: `EDITED`.
5. Sin flags, `exif_score ≤ 0.20` y `ela_score < 0.15`: `AUTHENTIC`.
6. Cualquier otro caso: `INCONCLUSIVE`.

`AUTHENTIC` es una clasificación conservadora, no una certificación. Si Gemini falla, la clasificación es `INCONCLUSIVE`, `cognitive_available=false` y se agrega `cognitive_analysis_unavailable`.

## 9. Cálculo del riesgo de la imagen

Las señales numéricas presentes son:

```text
exif_score, ela_score y dct_benford_score cuando aplica
```

No hay pesos individuales: primero se obtiene su promedio simple. Las flags se deduplican aunque estén repetidas en `ai_flags` y `gemini_flags`.

```text
flags_factor = min(1, cantidad_de_flags_distintas / 3)
signal_mean = promedio de scores numéricos presentes
riesgo_base = 0.70 × signal_mean + 0.30 × flags_factor
fraud_score = max(riesgo_base, piso_semántico)
```

Pisos semánticos:

| Clasificación derivada de flags | Piso mínimo de `fraud_score` |
|---|---:|
| `AI_GENERATED` | `0.75` |
| `AI_MODIFIED` | `0.75` |
| `EDITED` | `0.40` |
| `SCREENSHOT` | `0.00` |
| Sin clasificación por flags | `0.00` |

Si no existe ninguna señal numérica, el riesgo es `max(flags_factor, piso_semántico)`. El valor final se limita a `[0,1]` y se redondea a 4 decimales.

### Ejemplos calculados

Imagen JPEG sin flags, EXIF `0.15`, ELA `0.10`, DCT `0.20`:

```text
signal_mean = (0.15 + 0.10 + 0.20) / 3 = 0.15
flags_factor = 0
fraud_score = 0.70 × 0.15 = 0.105
```

Imagen con EXIF `0.20`, ELA `0.30` y una flag `cloned_region`:

```text
signal_mean = 0.25
flags_factor = 1/3 = 0.3333
riesgo_base = 0.70×0.25 + 0.30×0.3333 = 0.275
piso EDITED = 0.40
fraud_score = 0.40
```

Imagen con flag confirmada `ai_generation_artifacts`, incluso con señales técnicas bajas:

```text
piso AI_GENERATED = 0.75
fraud_score ≥ 0.75
```

Por ello una detección IA confirmada nunca termina `APPROVED` y, con exactamente `0.75`, termina `REJECTED` porque el umbral de rechazo es mayor que `0.70`.

## 10. Veredicto y porcentajes

Con un solo artefacto, su `fraud_score` es el score global. Los límites exactos son:

| `fraud_score` | Veredicto |
|---:|---|
| `< 0.40` | `APPROVED` |
| `0.40` a `0.70`, incluidos | `SUSPICIOUS` |
| `> 0.70` | `REJECTED` |

```text
risk_percentage = round(fraud_score × 100)
authenticity_percentage = round((1 - fraud_score) × 100)
```

Si Gemini no estuvo disponible y el cálculo normal daría `APPROVED`, el veredicto cambia a `INCONCLUSIVE`, `analysis_complete=false` y `authenticity_percentage=null`. Si el riesgo técnico ya da `SUSPICIOUS` o `REJECTED`, conserva ese veredicto aunque el análisis esté incompleto.

## 11. Valores entregados

En una consulta autenticada del propietario, `analysis` contiene:

| Campo | Tipo/valores |
|---|---|
| `exif_score` | Número `[0,1]` |
| `ela_score` | Número `[0,1]` |
| `dct_benford_score` | Número `[0,1]` o `null` |
| `benford_applicable` | `true` solo para JPEG |
| `gemini_flags`, `ai_flags` | Lista de flags confirmadas |
| `image_classification` | `AI_GENERATED`, `AI_MODIFIED`, `SCREENSHOT`, `EDITED`, `AUTHENTIC` o `INCONCLUSIVE` |
| `image_classification_message` | Explicación corta |
| `ela_heatmap_url` | Ruta protegida al PNG |
| `cognitive_available` | Disponibilidad de Gemini |
| `analysis_warnings` | Advertencias de degradación |

`consolidated` entrega `fraud_score`, `risk_percentage`, `authenticity_percentage`, `verdict`, `analysis_complete`, `dominant_artifact` y `policy_applied`. En modo demo se oculta gran parte del análisis y solo se entrega vista básica.

## 12. Qué significa el resultado

- `AI_GENERATED`: Gemini confirmó con dos evaluaciones al menos una señal fuerte de generación; riesgo mínimo 75%.
- `AI_MODIFIED`: confirmó inpainting o relleno generativo; riesgo mínimo 75%.
- `EDITED`: detectó clonación, composición, iluminación inconsistente o texto deformado; riesgo mínimo 40%.
- `SCREENSHOT`: identifica naturaleza de captura, pero por sí sola no aumenta el piso de fraude.
- `AUTHENTIC`: no hubo flags y EXIF/ELA fueron bajos; no prueba procedencia ni cadena de custodia.
- `INCONCLUSIVE`: faltó IA o las señales técnicas no permiten clasificar con claridad.
- `APPROVED/SUSPICIOUS/REJECTED`: decisión matemática global basada en el score; no es idéntica a `image_classification`.
