# Algoritmos utilizados en el análisis de documentos

## 1. Objetivo y mapa de implementación

El análisis documental combina parsing estructural de PDF, validación criptográfica, extracción híbrida de texto, OCR, reglas aritméticas, estadística de Benford, análisis visual de imágenes embebidas e inferencia semántica.

| Algoritmo | Implementación | Resultado |
|---|---|---|
| Validación PDF | `analysis_controller.py::_resolve_and_validate_artifact` | Artefacto `TEXT` o error |
| Inspección estructural | `pymupdf_structure_analyzer_adapter.py` | Score, flags y evidencia |
| Validación de firma | `_signature_evidence()` con pyHanko | Validez, integridad, confianza y DocMDP |
| Extracción híbrida/OCR | `deepseek_ocr_adapter.py` | Texto y métricas de cobertura |
| Consistencia aritmética | `document_consistency_service.py` | Checks, flags y score |
| Inferencia semántica | `deepseek_analyzer_adapter.py` | Tipo, montos y flags |
| Aplicabilidad Benford | `benford_applicability_service.py` | Booleano |
| Benford estadístico | `benford_statistical_adapter.py` | Score `[0,1]` |
| Análisis de imágenes internas | `_analyze_embedded_image()` | Evidencia visual agregada |
| Scoring/consolidación | Servicios `FraudScoring` y `Consolidation` | Riesgo y veredicto |

El flujo se orquesta en `ProcessAnalysisJobUseCase._analyze_text()`. El nombre `TEXT` incluye PDF porque representa el tipo lógico del artefacto, aunque internamente también se inspeccionen su estructura e imágenes.

## 2. Validación sintáctica del PDF

La API comprueba tamaño máximo de 50 MiB y firma `%PDF`. Después abre los bytes con `fitz.open(stream=..., filetype="pdf")`.

```text
si requiere contraseña → rechazar
si page_count < 1      → rechazar
si PyMuPDF no abre     → rechazar como corrupto/no PDF
si todo pasa           → artifact_type = TEXT
```

Esto es parsing sintáctico, no prueba de autenticidad. Tras validarlo, `SubmitAnalysisUseCase` guarda el original, crea el job y encola al worker.

## 3. Inspección estructural con PyMuPDF

### Fundamento

Un PDF es un grafo de objetos, páginas, streams, revisiones y metadatos. Alteraciones, contenido activo o inconsistencias de fechas pueden dejar evidencia estructural aunque el aspecto visible sea normal.

### Recorrido implementado

`PyMuPdfStructureAnalyzerAdapter._analyze_sync()` recorre todas las páginas y cuenta:

- anotaciones y widgets;
- campos de formulario y firma;
- fuentes únicas;
- rectángulos de texto e imagen superpuestos;
- capas opcionales y archivos embebidos.

También serializa objetos xref y busca marcadores `/JavaScript`, `/JS`, `/OpenAction`, `/Launch` y `/SubmitForm`. Las revisiones se estiman contando `%%EOF` y `startxref`; los incremental updates son `max(0, revisiones-1)`.

### Fechas

`_pdf_date_key()` extrae dígitos de las fechas PDF y compara las primeras 14 posiciones `YYYYMMDDhhmmss`. Si modificación es anterior a creación genera inconsistencia.

### Score

```text
candidatos = []
si estructura reparada:             candidatos += 0.40
si contenido activo:                candidatos += 0.70
si fechas inconsistentes:           candidatos += 0.35
si alguna firma inválida:           candidatos += 0.90
si DocMDP indica modificación:       candidatos += 0.90
pdf_structure_score = max(candidatos, default=0)
```

Usar el máximo evita sumar evidencias relacionadas, pero permite que una señal crítica domine dentro de este algoritmo.

### Evidencia sin puntuación

Software creador/editor, número de actualizaciones, anotaciones, archivos, capas, fuentes y solapamientos se devuelven para explicación, pero no añaden riesgo directamente.

## 4. Validación criptográfica de firmas con pyHanko

### Fundamento

Una firma PDF cubre bytes concretos del documento. Su validación distingue:

- validez criptográfica: la firma matemática coincide;
- integridad: los bytes cubiertos no fueron alterados indebidamente;
- confianza: el certificado encadena hacia una autoridad confiable disponible;
- DocMDP: las modificaciones posteriores respetan permisos del firmante.

### Implementación

`PdfFileReader` obtiene `embedded_signatures`. Para cada una, `validate_pdf_signature()` produce:

```text
validation_status
cryptographically_valid
intact
trusted
docmdp_ok
modification_level
signer_subject
```

El estado es `VALID` solo si `status.valid` y `status.intact` son verdaderos. Una excepción individual se registra como `ERROR`; un fallo general devuelve lista vacía para que el resto del pipeline continúe.

### Uso y matiz

Firma inválida o violación DocMDP produce score estructural 0.90. `trusted=false` se reporta, pero actualmente no suma riesgo; puede significar simplemente que falta la CA en el trust store.

## 5. Extracción híbrida de texto

### Fundamento

Los PDF digitales contienen texto extraíble; los escaneados contienen píxeles. Usar OCR siempre sería más lento y menos preciso, por lo que se selecciona por página.

### Algoritmo

`DeepSeekOcrAdapter._extract_from_pdf()` procesa como máximo `PDF_MAX_PAGES`, por defecto 10:

```text
para cada página:
    page_text = PyMuPDF.get_text().strip()
    si len(page_text) >= 50:
        conservar texto digital
        seleccionar imágenes embebidas para OCR complementario
    si no:
        rasterizar página a 150 DPI como PNG
        aplicar OCR remoto
```

Las imágenes menores de 128 píxeles por lado se omiten. Se deduplican por xref. El límite de imágenes OCR lo recibe el constructor desde `PDF_MAX_EMBEDDED_IMAGES`; Compose usa 5.

Separadamente conserva hasta cinco imágenes para análisis visual. Si hay más páginas que el límite, marca `truncated=true`.

### OCR remoto

`_ocr_image()` codifica la página/imagen como data URL Base64 y la envía a un endpoint compatible con OpenAI con el prompt “extraer todo el texto y no comentar”. El timeout es 120 segundos y las peticiones usan el helper de reintentos HTTP.

### Degradación

El fallo de una página produce `[OCR no disponible]` y una warning, sin detener las demás. Si falla la extracción completa pero existe resultado estructural, se entrega un análisis parcial. `ocr_available` queda falso cuando hay warnings.

### Complejidad

El parsing es aproximadamente lineal en páginas/objetos. OCR depende del número de páginas rasterizadas y del tamaño de las imágenes; es el paso con mayor latencia y coste externo.

## 6. Normalización de números

Antes de comprobar aritmética, `_number()` transforma formatos frecuentes:

- si hay coma y punto, el separador más a la derecha se considera decimal;
- una sola coma con uno o dos dígitos finales se trata como decimal;
- varias apariciones de punto se tratan como separadores de miles;
- se aceptan signos.

Antes de elegir el último número de una línea, el servicio elimina paréntesis y porcentajes para evitar confundir referencias o tasas con montos.

Este parser es heurístico: no conoce moneda, locale declarado ni estructura tabular completa.

## 7. Consistencia aritmética

### Extracción por reglas

Expresiones regulares detectan:

```text
cantidad × precio = total
subtotal/base imponible
IVA/impuesto/tax
total a pagar/importe total/grand total/total
```

Si una etiqueta no tiene monto en su línea, revisa la siguiente para soportar tablas extraídas como columnas separadas.

### Tolerancia

Para toda igualdad:

```text
difference = |reported - expected|
tolerance = max(0.02, |reported| × 0.001)
passed = difference ≤ tolerance
```

Es una tolerancia mínima de dos centavos o 0,1%.

### Riesgo

```text
relative = difference / max(|reference|, 1)
risk = min(1, max(0.4, relative × 10))
document_consistency_score = max(riesgos_de_checks_fallidos, default=0)
```

Toda inconsistencia empieza en 0.40. Si hubo comprobaciones pero ninguna falla, el score es 0; si no fue posible comprobar nada, es `null` y no entra al scoring.

### Uso

`_analyze_text()` añade `consistency.flags` a `ai_flags` y guarda checks detallados. Por eso una inconsistencia influye de dos maneras: como score numérico y como flag dentro de `flags_factor`.

## 8. Inferencia semántica con DeepSeek

### Naturaleza

Es inferencia de un modelo remoto, no un algoritmo determinista. Su objetivo es clasificar el documento, extraer montos y generar hallazgos semánticos conservadores.

### Implementación

`DeepSeekAnalyzerAdapter.analyze()` limita el texto a 12.000 caracteres, usa temperatura 0 y exige JSON:

```json
{
  "document_type": "invoice|receipt|...|other",
  "financial_amounts": [10.5, 200],
  "ai_findings": [
    {"flag": "possible_ai_edited_text", "confidence": "HIGH", "evidence": "..."}
  ]
}
```

`_parse_json_object()` tolera fences Markdown o texto previo buscando el primer objeto JSON válido. Solo conserva findings HIGH con evidencia.

Las flags `possible_ai_generated_text` y `possible_ai_edited_text` disparan una segunda consulta escéptica. La primera hipótesis se elimina si no se confirma nuevamente en HIGH.

### Salida y fallos

Devuelve `TextCognitiveResult(document_type, financial_amounts, ai_flags)`. Ante error, el caso de uso usa tipo `null`, montos vacíos, flags vacías, `cognitive_available=false` y una warning. La estructura y consistencia local permanecen.

## 9. Aplicabilidad de Benford documental

Benford no es válido para cualquier conjunto de números. `BenfordApplicabilityService` exige simultáneamente:

```text
tipo ∈ {invoice, receipt, bank_statement, financial_report,
        budget, payroll, tax_document, purchase_order}
cantidad de montos no cero ≥ BENFORD_MIN_AMOUNT_COUNT (30 por defecto)
max(|montos|) / min(|montos|) ≥ 100
valores únicos / cantidad ≥ 0.50
```

Estas reglas evitan usar Benford en identificadores, fechas, muestras pequeñas, rangos estrechos o series muy repetidas.

Si no aplica, `benford_score=null`; una señal no aplicable se excluye, no se transforma en cero.

## 10. Benford estadístico

Para cada monto útil se toma el primer dígito significativo. La distribución esperada es:

```text
P(d) = log10(1 + 1/d)
```

Se calcula distancia de variación total:

```text
TV = 0.5 × Σd |observado(d) - esperado(d)|
benford_score = min(1, TV/0.30)
```

Aunque el adapter acepta un mínimo técnico de cinco datos, la regla documental previa exige al menos 30. El mismo adapter se reutiliza para coeficientes DCT de imágenes, donde aplica el mínimo técnico.

## 11. Algoritmos sobre imágenes embebidas

`_analyze_embedded_image()` ejecuta concurrentemente EXIF, ELA y Gemini mediante `asyncio.gather(..., return_exceptions=True)`. DCT/Benford se añade para JPEG.

```text
technical_score = promedio de EXIF, ELA y DCT presentes
document_visual_score = máximo technical_score entre imágenes
```

La concurrencia de llamadas Gemini se limita con `asyncio.Semaphore(PDF_IMAGE_ANALYSIS_CONCURRENCY)`, por defecto 2. SHA-256 identifica imágenes duplicadas y agrega `duplicate_of`.

Una heurística geométrica asigna roles `SIGNATURE_CANDIDATE`, `SEAL_OR_LOGO_CANDIDATE`, `GRAPHIC` o `PHOTO_OR_SCAN`. No reconoce semánticamente una firma; solo clasifica forma y tamaño.

Las flags visuales se agregan a `ai_flags` del documento, por lo que pueden imponer pisos de riesgo de generación IA 0.75, modificación IA 0.75 o edición 0.40.

## 12. Scoring documental

`ArtifactAnalysis.numeric_scores()` selecciona solo valores no nulos:

```text
benford_score
document_consistency_score
document_visual_score
pdf_structure_score
```

Luego `FraudScoringService` aplica:

```text
flags_factor = min(1, flags_distintas / 3)
signal_mean = promedio(scores presentes)
combined = 0.70 × signal_mean + 0.30 × flags_factor
fraud_score = max(combined, piso_semántico)
```

Pisos: texto posiblemente generado `0.65`; texto posiblemente editado `0.50`; imagen generada/modificada `0.75`; imagen editada `0.40`.

### Consecuencia de implementación

Los scores técnicos se promedian con el mismo peso. Una firma inválida produce `pdf_structure_score=0.90`, pero puede diluirse si existen varias señales en cero. Además, `pdf_structure_flags` no se unen actualmente a `ai_flags`. Si el requisito es que una firma inválida fuerce rechazo, se debería introducir un piso estructural o agregar flags estructurales al motor de reglas.

## 13. Consolidación y completitud

`ProcessAnalysisJobUseCase.execute()` procesa artefactos en paralelo con `asyncio.gather`. Cada fallo queda aislado. El job es `COMPLETED` si al menos uno termina y `FAILED` si todos fallan.

Un artefacto es incompleto cuando `ocr_available` o `cognitive_available` es falso. `ConsolidationService` toma el peor caso por defecto o promedio ponderado opcional.

```text
score < 0.40       → APPROVED
0.40 ≤ score ≤0.70 → SUSPICIOUS
score > 0.70       → REJECTED
```

Un `APPROVED` incompleto se transforma en `INCONCLUSIVE`. Los resultados sospechosos/rechazados no se rebajan por falta de un proveedor.

## 14. Ensamblaje en el worker

`app/worker.py::build_process_job_use_case()` inyecta:

- `PyMuPdfStructureAnalyzerAdapter`;
- `DeepSeekOcrAdapter`;
- `DocumentConsistencyService`;
- `DeepSeekAnalyzerAdapter`;
- `BenfordApplicabilityService` y `BenfordStatisticalAdapter`;
- adaptadores EXIF, ELA, DCT y Gemini para imágenes;
- `FraudScoringService` y `ConsolidationService`.

Los límites se configuran con `PDF_MAX_PAGES`, `PDF_MAX_EMBEDDED_IMAGES`, `PDF_IMAGE_ANALYSIS_CONCURRENCY`, `BENFORD_MIN_AMOUNT_COUNT` y `CONSOLIDATION_POLICY`. Las URLs, modelos y claves de proveedores también llegan por entorno.

## 15. Pruebas asociadas

- `test_pdf_structure_analyzer.py`;
- `test_deepseek_ocr_adapter.py`;
- `test_deepseek_analyzer_adapter.py`;
- `test_document_consistency_service.py`;
- `test_benford_applicability_service.py`;
- `test_dct_benford_adapters.py`;
- `test_process_analysis_job_use_case.py`;
- pruebas de adaptadores visuales y consolidación.

La separación por puertos permite probar reglas sin MongoDB, MinIO, Celery o proveedores reales y sustituir cada implementación sin modificar el caso de uso.
