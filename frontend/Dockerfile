# DeepForense — frontend (React + Vite)

# --- Etapa dev: servidor de Vite con hot-reload (uso local, docker-compose.yml) ---
FROM node:20-alpine AS dev
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- Etapa build: compila los assets estáticos ---
# VITE_API_BASE_URL se "hornea" dentro del bundle en build-time (Vite), no en
# runtime — por eso se recibe como build ARG y no como variable de entorno del
# contenedor final (a diferencia del target "dev", que sí la lee en runtime).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- Etapa prod: sirve los assets con nginx como usuario no-root (docker-compose.prod.yml) ---
FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
