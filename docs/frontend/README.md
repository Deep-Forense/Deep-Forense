# Frontend

SPA de DeepForense construida con React 18, Vite 6, React Router, Axios, Tailwind CSS 4 y Framer Motion.

## Funciones

- Landing pública y análisis demo.
- Registro, login, logout y persistencia local de sesión.
- Dashboard protegido con carga de archivos o URL, polling de jobs, visualización del resultado, heatmap ELA e historial paginado.
- Adaptación de resultados de backend a un modelo de presentación en `scan.service.js`.

## Estructura

```text
src/
├── api/client.js                  Cliente Axios e interceptor JWT
├── components/                   Atomic Design: atoms, molecules, organisms, templates
├── features/auth/                 Servicio y ruta protegida
├── features/scan/                 Servicios, hooks, dominio y componentes de análisis
├── pages/                         Landing, login, registro y dashboard
├── routes/                        Router y rutas
└── styles/global.css
```

Rutas del navegador: `/`, `/login`, `/register` y `/dashboard`. Las rutas desconocidas regresan a la landing. Nginx usa fallback a `index.html` para soportar React Router.

## Configuración y ejecución

Solo utiliza `VITE_API_BASE_URL`; por defecto apunta a `http://localhost:8000`. Todas las llamadas pasan por Kong.

```bash
npm ci
npm run dev       # http://localhost:5173
npm run build     # salida en dist/
npm run preview
```

En Docker existen targets `dev`, `build` y `prod`. En producción Vite incorpora `VITE_API_BASE_URL` durante el build y Nginx no privilegiado sirve el resultado en el puerto interno 8080.

## Sesión y API

`src/api/client.js` agrega `Authorization: Bearer <token>` desde `deepforense_token` en localStorage. `auth.service.js` conserva además `deepforense_user`. El logout remoto no revoca el JWT; el bloque `finally` elimina la sesión local.

El escaneo crea un job y consulta `GET /api/forensic/jobs/{id}` cada 1,5 s, hasta 40 intentos (aproximadamente 60 s). Los heatmaps se descargan como blob autenticado y se muestran mediante object URL.

## Consideraciones de mantenimiento

- No hay scripts de test, lint o typecheck en `package.json`; agregarlos antes de ampliar funcionalidades.
- `mode` se recibe en los servicios de escaneo pero actualmente no se envía al backend.
- `src/services/api.ts` es un módulo vacío; debe eliminarse o adquirir una responsabilidad clara.
- No existe interceptor global de respuestas para expirar una sesión ante 401.
- localStorage expone el token ante XSS; revisar la estrategia descrita en la auditoría.
