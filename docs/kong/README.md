# Kong Gateway

Kong 3.7 funciona en modo DB-less y constituye el único punto de entrada HTTP de los servicios de aplicación. Su fuente declarativa es `kong/kong.yml`.

## Enrutamiento

| Ruta externa | Upstream | `strip_path` |
|---|---|---:|
| `/api/auth/*` | `http://auth-service:8080` | No |
| `/api/forensic/*` | `http://forensic-api:8000` | No |
| `/auth-docs/*` | `http://auth-service:8080` | Sí |
| `/forensic-docs/*` | `http://forensic-api:8000` | Sí |

La ruta de documentación de Auth agrega `X-Forwarded-Prefix: /auth-docs`. Forensic API recibe `ROOT_PATH=/forensic-docs`. Estas configuraciones permiten que los recursos y contratos Swagger generen URLs correctas detrás del prefijo.

## Plugins

- `cors` global: métodos GET, POST, PUT, DELETE y OPTIONS; headers Accept, Authorization y Content-Type; credenciales habilitadas.
- `rate-limiting` en `auth-routes`: 10 solicitudes/minuto, política local y tolerancia a fallos.
- `request-transformer` en la documentación de Auth.

## Operación

```bash
docker compose up kong
curl http://localhost:8001/status       # solo desarrollo
curl http://localhost:8000/forensic-docs/openapi.json
```

El proxy se publica en 8000 en todos los entornos. El Admin API 8001 se publica únicamente por `docker-compose.override.yml`. Para aplicar cambios declarativos se recrea/reinicia el contenedor.

## Seguridad pendiente

La regex CORS actual permite cualquier origen HTTP/HTTPS aunque existe una lista explícita, y `credentials` está habilitado. Debe eliminarse para producción. También se recomienda retirar las rutas Swagger en producción, aplicar rate limiting únicamente al endpoint de login y usar almacenamiento compartido si Kong se replica. Kong enruta JWT pero no lo valida: la autorización final reside en cada servicio.
