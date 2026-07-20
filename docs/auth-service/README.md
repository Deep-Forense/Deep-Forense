# Auth Service

Microservicio de identidad construido con Java 21, Spring Boot 3.3, Spring Security, JPA/PostgreSQL, BCrypt, JJWT y springdoc.

## Responsabilidad y arquitectura

Registra usuarios, verifica credenciales, emite/valida JWT y devuelve el perfil autenticado. Sigue separación hexagonal:

```text
domain/          User, value objects, eventos, excepciones y puertos
application/     Casos de uso, puertos de entrada y DTO
infrastructure/  REST, JPA, BCrypt, JWT, Security y configuración
```

## Endpoints

| Método y ruta | Acceso | Respuesta |
|---|---|---|
| `POST /api/auth/register` | Público | 201 con id, nombre y email; 409 duplicado |
| `POST /api/auth/login` | Público | JWT, tipo, expiración y usuario; 401 inválido |
| `POST /api/auth/logout` | JWT | 204; no revoca el token |
| `GET /api/auth/me` | JWT | id, nombre, email y fecha de creación |

Ejemplo de login:

```json
{"email":"usuario@example.com","password":"secreto123"}
```

El JWT usa una clave HMAC, lleva email en `sub`, UUID en `userId`, `iat` y `exp`. La sesión es stateless. La contraseña requiere al menos ocho caracteres y se persiste hasheada con BCrypt. El email se normaliza/valida mediante el value object `Email`.

## Configuración

| Variable | Uso |
|---|---|
| `SPRING_DATASOURCE_URL` | JDBC PostgreSQL |
| `SPRING_DATASOURCE_USERNAME` | Usuario DB |
| `SPRING_DATASOURCE_PASSWORD` | Contraseña DB |
| `JWT_SECRET` | Clave HMAC; debe tener al menos 32 bytes para HS256 |
| `JWT_EXPIRATION_MS` | Vigencia, default 3.600.000 ms |

`server.forward-headers-strategy=framework` permite que Swagger funcione bajo `/auth-docs` mediante Kong. JPA usa actualmente `ddl-auto: update`.

## Desarrollo

```bash
mvn spring-boot:run
mvn test
mvn package
```

Se necesita PostgreSQL en `localhost:5432/deepforense_auth` o variables equivalentes. Swagger local se genera en `/swagger-ui.html` y `/v3/api-docs`; mediante Kong queda bajo `/auth-docs`.

## Seguridad y operación

- Registro y login son públicos; el resto requiere Bearer válido.
- CSRF está deshabilitado porque la API usa JWT en header y no sesiones.
- Logout solo instruye al cliente a descartar el token; no hay blacklist ni refresh tokens.
- Sustituir defaults, migrar a secretos gestionados y añadir `iss`/`aud` o firma asimétrica.
- Reemplazar `ddl-auto: update` por Flyway/Liquibase.
- `/health` está permitido por seguridad pero no implementado; añadir Actuator y un healthcheck de Compose.
- Las pruebas actuales cubren `Email` y `RawPassword`; faltan casos de uso, JWT, REST, JPA y seguridad integrados.
