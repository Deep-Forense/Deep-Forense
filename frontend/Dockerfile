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
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Etapa prod: sirve los assets con nginx como usuario no-root (docker-compose.prod.yml) ---
FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
