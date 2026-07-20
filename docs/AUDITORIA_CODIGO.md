# Auditoría de código de DeepForense

## Alcance y método

Revisión estática de frontend, Kong, forensic-api, forensic-worker, auth-service, Dockerfiles, Compose, contrato OpenAPI y pruebas existentes. Fecha: 20 de julio de 2026. No se modificó código productivo.

La validación `docker compose config --quiet` terminó correctamente. Las suites no pudieron ejecutarse completamente en este entorno: Python 3.11 no está instalado; Maven no pudo descargar el parent POM por bloqueo de red; y esbuild no tuvo permiso para recorrer una ruta superior del workspace. Son limitaciones de la estación de auditoría, no resultados negativos de las pruebas.

## Resumen ejecutivo

La solución tiene separación de responsabilidades coherente, un pipeline asíncrono real y buenas defensas en la ingesta (validación por contenido, límite de 50 MB y mitigaciones SSRF en el descargador). Los riesgos prioritarios están en configuración de seguridad para producción, gobierno de esquemas y cobertura/automatización de pruebas.

| Severidad | Cantidad | Prioridad |
|---|---:|---|
| Alta | 3 | Corregir antes de exponer producción |
| Media | 7 | Siguiente ciclo técnico |
| Baja | 4 | Mantenimiento planificado |

## Hallazgos

### Alta

1. **CORS global permite cualquier origen con credenciales.** `kong/kong.yml` incluye orígenes concretos y también una regex equivalente a cualquier `http(s)`, mientras `credentials: true`. Esto anula la lista blanca y amplía el origen de peticiones autenticadas. Eliminar la regex y parametrizar una lista explícita por entorno.

2. **Credenciales inseguras como fallback.** Compose y servicios aceptan contraseñas conocidas y `JWT_SECRET=change-this-secret-in-production`. Un despliegue con `.env` incompleto arrancaría de forma insegura. En producción, exigir secretos sin default, almacenarlos en un secret manager y validar longitud/entropía al iniciar.

3. **JWT compartido simétrico entre servicios sin separación de confianza.** Cualquier servicio con `JWT_SECRET` puede emitir tokens válidos; forensic-api admite HS256/384/512 y no valida emisor ni audiencia. Fijar HS256 si se conserva el diseño actual y validar `iss`/`aud`; preferiblemente usar firma asimétrica, donde auth conserva la clave privada y consumidores solo reciben la pública.

### Media

4. **Swagger de ambos servicios sigue enrutado por Kong en producción.** El override productivo no elimina `/auth-docs` ni `/forensic-docs`. Deshabilitar documentación o restringirla por red/autenticación fuera de desarrollo.

5. **CORS y dominios están codificados en el archivo declarativo.** Mezcla configuración local, IP y producción; obliga a cambiar/reconstruir configuración. Generar configuración por ambiente o usar plantillas controladas en despliegue.

6. **Rate limiting no está limitado al login.** El plugin está en toda la ruta `/api/auth`, por lo que registro, logout y `/me` comparten 10 solicitudes/minuto por consumidor/IP; además `policy: local` no coordina múltiples instancias. Crear una ruta específica para login y usar un backend compartido al escalar.

7. **Esquema de Auth gestionado con `ddl-auto: update`.** No existe control versionado de migraciones ni rollback. Incorporar Flyway/Liquibase y usar `validate` en producción.

8. **Imágenes de infraestructura no fijadas por digest y algunas usan `latest`.** MinIO, `minio/mc` y Swagger UI pueden cambiar sin modificación del repositorio. Fijar versiones/digests y automatizar actualizaciones verificadas.

9. **Token en `localStorage`.** Una vulnerabilidad XSS permitiría extraer el JWT. Considerar cookie `HttpOnly`, `Secure`, `SameSite` con protección CSRF; si se mantiene localStorage, endurecer CSP y evitar HTML no confiable.

10. **Logout no revoca tokens.** El endpoint devuelve 204 y solo el cliente elimina el token; un token copiado funciona hasta expirar. Documentar esta semántica y añadir rotación/revocación si el modelo de amenaza lo requiere.

### Baja

11. **Endpoint `/health` permitido pero no implementado en auth-service.** SecurityConfig lo declara público, pero no existe controlador/Actuator. Añadir Spring Actuator y healthcheck en Compose para que Kong espere disponibilidad real.

12. **API deprecada de ciclo de vida en FastAPI.** `@app.on_event("startup")` funciona en la versión actual, pero debe migrarse a `lifespan` para futuras versiones.

13. **Código frontend residual o parámetros sin uso.** `src/services/api.ts` exporta un objeto vacío y `mode` no altera las solicitudes de escaneo. Eliminarlo o implementar la intención para reducir ambigüedad.

14. **Desajuste de documentación histórica.** El README raíz afirma que el proyecto es un esqueleto con stubs, pero el repositorio contiene pipeline y pruebas reales. Actualizarlo para apuntar a esta documentación.

## Aspectos positivos verificados

- Servicios de negocio con límites hexagonales claros e inyección de puertos.
- Servicios de aplicación no publicados directamente al host en Compose base.
- Contenedores productivos ejecutados como usuarios no root.
- Validación del archivo por magic bytes y apertura real del PDF, no por nombre/MIME.
- Descarga de URL con límites de tamaño, redirects controlados y validaciones contra SSRF.
- Ownership aplicado al historial, detalle completo y heatmaps.
- Cliente Mongo del worker creado tras fork; reduce problemas de seguridad de procesos.
- Fallos cognitivos degradan a evidencia técnica/inconclusa en vez de declarar autenticidad.
- Redis usa AOF y snapshots; MinIO se inicializa de forma idempotente.
- Hay pruebas unitarias relevantes en ambos servicios forenses.

## Cobertura y deuda de pruebas

- Frontend no declara framework ni scripts de test/lint/typecheck.
- Auth solo contiene pruebas de `Email` y `RawPassword`; faltan controlador, repositorio, JWT, seguridad e integración PostgreSQL.
- Kong no tiene pruebas automatizadas de rutas, CORS, prefijos Swagger o límites.
- Faltan pruebas end-to-end del flujo `registro → login → carga → worker → consulta` con infraestructura real o Testcontainers.
- CI debería ejecutar builds, tests, análisis de dependencias, escaneo de imágenes/secretos y validación OpenAPI contra implementaciones.

## Plan recomendado

1. Cerrar CORS, exigir secretos y endurecer JWT.
2. Ocultar documentación y Admin API en producción; separar rate limit de login.
3. Introducir migraciones de PostgreSQL y fijar imágenes.
4. Añadir healthchecks/Actuator y políticas de timeout/retry observables.
5. Crear tests frontend, integración de auth, smoke tests de Kong y una prueba E2E.
6. Incorporar métricas, trazas/correlation ID y alertas de cola, fallos y latencia.
