# Flujo completo de análisis de documentos

## 1. Alcance y limitación actual

DeepForense analiza documentos PDF subidos como archivo. Aunque el formulario de la API tiene un campo genérico `url`, **el código actual no admite documentos mediante URL**: el caso de uso de URL exige que el contenido final sea una imagen JPEG, PNG o WEBP.

Por tanto:

| Entrada solicitada | Estado actual |
|---|---|
| PDF mediante `file` | Soportado |
| PDF mediante `url` | No soportado; HTTP 400 |
| Página web con enlace/visor de PDF | No soportado; HTTP 400 |

Para soportar documentos por URL habría que crear o ampliar un caso de uso que descargue PDF con las mismas protecciones SSRF/tamaño, valide `%PDF`, abra el archivo con PyMuPDF y lo almacene como artefacto `TEXT`. No se documenta ese flujo como existente porque hoy no está implementado.

> El sistema busca indicadores técnicos, visuales, aritméticos y cognitivos. No certifica legalmente la autenticidad de un documento ni sustituye la validación de identidad, firma o fuente emisora.

## 2. Ingreso de un PDF por archivo

### 2.1 Solicitud

- Demo: `POST /api/forensic/demo/analyze`.
- Autenticado: `POST /api/forensic/analyze` con JWT.
- Content-Type: `multipart/form-data`.
- Campo: `file`.

### 2.2 Validaciones

| Validación | Regla | Error |
|---|---|---|
| Exclusividad | Debe enviarse `file` o `url`, nunca ambos | HTTP 400 |
| Archivo vacío | No permitido | HTTP 400 |
| Tamaño | Máximo 50 MiB | HTTP 413 |
| Firma | Debe comenzar con `%PDF` | HTTP 400 |
| Integridad | PyMuPDF debe poder abrirlo | HTTP 400 |
| Contraseña | `needs_pass` debe ser falso | HTTP 400 |
| Páginas | Debe contener al menos una | HTTP 400 |

El PDF se guarda en MinIO como `uploads/{uuid}-{nombre}`, se crea un artefacto `TEXT`, el job queda `PENDING` en MongoDB y se encola `process_analysis_job` en Redis. El worker lo cambia a `PROCESSING`.

## 3. Pipeline general

```text
PDF por archivo
     │
     ▼
Validación → MinIO → Mongo/PENDING → Redis/Celery → PROCESSING
                                                     │
                  ┌──────────────────────────────────┼─────────────────────────┐
                  ▼                                  ▼                         ▼
       Estructura y firmas PDF              Extracción texto/OCR       Imágenes embebidas
                  │                                  │                         │
                  │                       ┌──────────┴──────────┐       EXIF + ELA + DCT
                  │                       ▼                     ▼              + Gemini
                  │               Consistencia           DeepSeek texto
                  │                 aritmética            + montos/tipo
                  └───────────────────────┬─────────────────────┴───────────────┘
                                          ▼
                                  Benford si aplica
                                          ▼
                              Score, consolidación y veredicto
```

## 4. Análisis estructural del PDF

PyMuPDF y pyHanko inspeccionan:

- metadatos, creador y productor;
- software de edición detectado: Photoshop, Illustrator, Acrobat, LibreOffice, Word o Canva;
- número de revisiones/incremental updates;
- estructura reparada;
- anotaciones, formularios y campos de firma;
- archivos embebidos y capas opcionales;
- cantidad de fuentes únicas;
- solapamientos texto–imagen;
- contenido activo: JavaScript, OpenAction, Launch o SubmitForm;
- firmas digitales, integridad, confianza, DocMDP, nivel de modificación y firmante.

### 4.1 Puntuación estructural

Cada condición agrega una flag y un candidato de riesgo; `pdf_structure_score` es el máximo, no la suma.

| Hallazgo | Flag | Candidato |
|---|---|---:|
| PDF reparado al abrir | `pdf_repaired_structure` | `0.40` |
| Contenido activo sospechoso | `pdf_suspicious_active_content` | `0.70` |
| Fecha de modificación anterior a creación | `pdf_metadata_date_inconsistency` | `0.35` |
| Firma digital inválida | `pdf_invalid_digital_signature` | `0.90` |
| Documento modificado contra DocMDP después de firmar | `pdf_modified_after_signature` | `0.90` |

Ejemplo: PDF reparado (`0.40`) con JavaScript (`0.70`) y firma inválida (`0.90`) produce `pdf_structure_score=0.90`.

La detección de software de edición se entrega como evidencia, pero actualmente no suma por sí sola al score. Tampoco suman automáticamente anotaciones, capas, fuentes, archivos embebidos o solapamientos; se reportan para revisión.

## 5. Extracción de texto y OCR

El límite predeterminado es `PDF_MAX_PAGES=10`. Si el PDF tiene más páginas, `document_truncated=true` y solo se analizan las primeras 10.

Por cada página:

1. PyMuPDF extrae la capa de texto.
2. Si contiene al menos 50 caracteres, se usa como texto digital.
3. Si tiene menos de 50, la página se rasteriza a 150 DPI y se envía al proveedor OCR.
4. En páginas con texto digital también se pueden enviar imágenes embebidas al OCR.

Límites predeterminados:

| Elemento | Valor |
|---|---:|
| Páginas analizadas | 10 |
| Imágenes embebidas enviadas al OCR | 5 por configuración Compose |
| Imágenes distintas para análisis visual | 5, constante interna |
| Lado mínimo de imagen embebida | 128 píxeles |

Se deduplican imágenes por xref durante extracción y por SHA-256 en la evidencia visual. El resultado registra:

- `document_page_count`;
- `document_analyzed_pages`;
- `document_text_layer_pages`;
- `document_ocr_pages`;
- `document_embedded_images`;
- `document_truncated`;
- `ocr_available` y advertencias por página/imagen.

Si todo el OCR falla pero existe análisis estructural, el sistema conserva la estructura y marca el análisis incompleto. Si tampoco existe estructura, el artefacto falla.

## 6. Consistencia aritmética

El servicio busca cantidades, precio unitario, subtotal, impuestos/IVA y total. Soporta separadores `,` y `.`, multiplicadores `x`, `×` o `*`, y tolera que etiqueta y valor estén en líneas consecutivas.

### 6.1 Reglas

| Regla | Comparación |
|---|---|
| `subtotal_plus_tax_equals_total` | subtotal + impuesto = total |
| `quantity_times_unit_price` | cantidad × precio unitario = total de línea |
| `line_items_sum_equals_subtotal` | suma de líneas = subtotal |

Una comprobación pasa si:

```text
diferencia ≤ max(0.02, |valor_reportado| × 0.001)
```

Esto equivale a tolerar al menos 2 centavos o 0,1% del valor reportado.

Cuando falla:

```text
riesgo_inconsistencia = min(1, max(0.4, (diferencia / max(|referencia|, 1)) × 10))
```

`document_consistency_score` es el mayor riesgo de todas las inconsistencias. Si hubo checks y todos pasaron, vale `0.0`; si no se pudo ejecutar ninguna regla, vale `null` y no entra al promedio.

Flags generadas: `arithmetic_total_mismatch`, `line_item_total_mismatch` y `line_items_subtotal_mismatch`.

Ejemplo: total reportado 100, esperado 95, diferencia 5:

```text
riesgo = max(0.4, (5/100)×10) = 0.50
```

## 7. Análisis semántico con DeepSeek

Se analizan como máximo los primeros 12.000 caracteres extraídos. La temperatura es 0 y se exige respuesta JSON.

### 7.1 Tipo documental

Puede devolver: `invoice`, `receipt`, `bank_statement`, `financial_report`, `budget`, `payroll`, `tax_document`, `purchase_order`, `contract`, `id_document`, `letter`, `academic`, `news` u `other`.

También entrega una lista numérica `financial_amounts`.

### 7.2 Flags cognitivas

- `possible_ai_generated_text`;
- `possible_ai_edited_text`;
- `inconsistent_totals`;
- `generic_template_text`;
- `missing_tax_id`;
- `date_inconsistency`.

Solo se conservan findings `HIGH` con evidencia localizable. Las dos flags de origen IA requieren una segunda evaluación escéptica; sobreviven únicamente si ambas consultas coinciden.

Pisos de riesgo de las flags de texto:

| Flag | Piso mínimo del score final del artefacto |
|---|---:|
| `possible_ai_generated_text` | `0.65` |
| `possible_ai_edited_text` | `0.50` |

Las demás flags aumentan `flags_factor`, pero no tienen piso propio. Detectar texto posiblemente generado por IA no significa automáticamente documento fraudulento: produce como mínimo un resultado `SUSPICIOUS`, salvo que otras señales lleven el riesgo por encima de 0.70.

Las flags Gemini de imágenes embebidas también terminan en `ai_flags` del documento. Por ello pueden imponer estos pisos adicionales: `AI_GENERATED=0.75`, `AI_MODIFIED=0.75` y `EDITED=0.40`; las flags de captura no tienen piso.

## 8. Benford para montos financieros

Solo aplica si se cumplen todas estas condiciones:

1. El tipo está entre los ocho tipos financieros: invoice, receipt, bank statement, financial report, budget, payroll, tax document o purchase order.
2. Hay al menos `BENFORD_MIN_AMOUNT_COUNT`, por defecto 30, montos no cero.
3. `máximo/mínimo ≥ 100`, es decir, al menos dos órdenes de magnitud.
4. `valores_únicos/cantidad ≥ 0.5`.

Si no aplica, `benford_applicable=false` y `benford_score=null`; no penaliza el documento.

Cuando aplica:

```text
P(d) = log10(1 + 1/d)
TV = 0.5 × Σ |observado(d) - esperado(d)|
benford_score = min(1, TV / 0.30)
```

Valores altos representan mayor desviación. `TV=0.03 → 0.10`, `TV=0.15 → 0.50`, `TV≥0.30 → 1.00`.

## 9. Imágenes embebidas

Hasta cinco imágenes embebidas distintas y de al menos 128×128 se analizan con:

- EXIF: software de edición `+0.45`, fechas diferentes `+0.35`, fecha original eliminada `+0.15`;
- ELA: `min(1, mean_diff/25)` y heatmap;
- DCT/Benford solo si la imagen embebida es JPEG;
- Gemini con las mismas flags visuales y doble verificación crítica descritas en el flujo de imágenes.

El score técnico de cada imagen embebida es el promedio simple de EXIF, ELA y DCT presentes:

```text
technical_score = promedio(exif_score, ela_score, dct_benford_score aplicables)
```

`document_visual_score` toma el máximo `technical_score` de las imágenes, no el promedio. Las flags visuales se agregan a `ai_flags` del documento. El heatmap principal corresponde a la imagen con mayor score técnico.

Rol heurístico reportado:

| Condición | Rol |
|---|---|
| Relación de aspecto ≥2.5 y altura ≤500 | `SIGNATURE_CANDIDATE` |
| Aspecto 0.75–1.33 y dimensión máxima ≤800 | `SEAL_OR_LOGO_CANDIDATE` |
| Dimensión máxima ≤600 | `GRAPHIC` |
| Otro caso | `PHOTO_OR_SCAN` |

El rol describe geometría; no valida que sea realmente una firma o sello.

## 10. Cálculo del riesgo documental

Las señales numéricas presentes son:

```text
benford_score
document_consistency_score
document_visual_score
pdf_structure_score
```

Los valores `null` se excluyen. No hay pesos diferentes entre ellas: se promedian. Las flags de DeepSeek, consistencia e imágenes se deduplican.

```text
flags_factor = min(1, cantidad_de_flags_distintas / 3)
signal_mean = promedio de señales numéricas presentes
riesgo_base = 0.70 × signal_mean + 0.30 × flags_factor
fraud_score = max(riesgo_base, piso_semántico)
```

El `piso_semántico` es el máximo aplicable entre texto e imágenes: `possible_ai_generated_text=0.65`, `possible_ai_edited_text=0.50`, señal visual `AI_GENERATED=0.75`, `AI_MODIFIED=0.75` o `EDITED=0.40`.

El resultado se limita a `[0,1]` y se redondea a cuatro decimales. Si no hay señales numéricas:

```text
fraud_score = max(flags_factor, piso_semántico)
```

### Ejemplos calculados

PDF con estructura `0.0`, consistencia `0.0`, sin Benford, sin imágenes y sin flags:

```text
signal_mean = 0
fraud_score = 0
veredicto normal = APPROVED
```

PDF con estructura `0.40`, consistencia `0.50`, una flag aritmética y sin otras señales:

```text
signal_mean = (0.40 + 0.50) / 2 = 0.45
flags_factor = 1/3 = 0.3333
fraud_score = 0.70×0.45 + 0.30×0.3333 = 0.415
veredicto = SUSPICIOUS
```

PDF con firma inválida `0.90`, las demás señales en `0` y sin flags agregadas al factor:

```text
si solo están presentes estructura=0.90 y consistencia=0.0:
signal_mean = 0.45
fraud_score = 0.315
```

Este último ejemplo revela una característica importante del algoritmo actual: al promediar todas las señales presentes, una evidencia estructural grave puede diluirse con señales en cero. Las `pdf_structure_flags` se entregan, pero no se incorporan al `flags_factor`. Es una decisión implementada que conviene revisar si una firma inválida debe forzar rechazo.

PDF con `possible_ai_generated_text` confirmado:

```text
piso semántico = 0.65
fraud_score ≥ 0.65 → al menos SUSPICIOUS
```

## 11. Consolidación y resultado final

Con el comportamiento actual de ingesta hay un artefacto por job. Su score se convierte directamente en el score global. Si en el futuro hay varios artefactos:

- `worst_case_dominates` (default): toma el mayor riesgo;
- `weighted_average`: peso de tipo `IMAGE=0.70`, `TEXT=0.30`, normalizado entre los artefactos presentes.

Umbrales exactos:

| `fraud_score` | `verdict` |
|---:|---|
| `< 0.40` | `APPROVED` |
| `0.40` a `0.70`, incluidos | `SUSPICIOUS` |
| `> 0.70` | `REJECTED` |

```text
risk_percentage = round(fraud_score × 100)
authenticity_percentage = round((1-fraud_score) × 100)
```

Un análisis se considera incompleto si `cognitive_available=false` u `ocr_available=false`. Si el veredicto matemático sería `APPROVED`, se reemplaza por `INCONCLUSIVE` y `authenticity_percentage=null`. Un análisis incompleto con riesgo suficiente conserva `SUSPICIOUS` o `REJECTED`.

## 12. Valores entregados

| Campo | Significado |
|---|---|
| `document_type` | Tipo clasificado por DeepSeek |
| `financial_amounts` | Montos extraídos por análisis semántico |
| `ai_flags` | Flags cognitivas, aritméticas y visuales deduplicadas |
| `benford_applicable`, `benford_score` | Aplicabilidad y desviación financiera |
| `document_*pages` | Total, analizadas, con texto y con OCR |
| `document_embedded_images` | Número de imágenes encontradas |
| `document_truncated` | Si quedaron páginas fuera del límite |
| `document_consistency_score/checks` | Riesgo y evidencia aritmética |
| `document_visual_score/evidence` | Mayor riesgo técnico visual y detalle por imagen |
| `document_visual_heatmap_url` | Heatmap de la imagen dominante, para propietario |
| `pdf_structure_score/structure/flags` | Riesgo y evidencia estructural/firma |
| `ocr_available`, `cognitive_available` | Completitud de proveedores |
| `analysis_warnings` | Pasos degradados o no disponibles |

El objeto global `consolidated` contiene `fraud_score`, porcentajes, `verdict`, `analysis_complete`, artefacto dominante y política. El detalle completo solo se entrega al propietario autenticado; un análisis demo devuelve una vista básica.

## 13. Interpretación responsable

- `APPROVED`: riesgo calculado menor a 40% con las señales disponibles; no equivale a certificado auténtico.
- `SUSPICIOUS`: riesgo entre 40% y 70% o presencia confirmada de algunas señales IA.
- `REJECTED`: riesgo superior a 70%; requiere revisión de las evidencias concretas.
- `INCONCLUSIVE`: faltó OCR/análisis cognitivo y las señales restantes no justifican una conclusión.
- `possible_ai_generated_text`: sospecha lingüística confirmada dos veces por el modelo, no prueba de autoría.
- Firma `VALID` e `intact`: comprobación criptográfica local; `trusted` depende de la cadena de confianza disponible.
- Consistencia matemática correcta no demuestra origen legítimo, y una inconsistencia puede ser error humano en lugar de fraude.
