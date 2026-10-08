# syntax=docker/dockerfile:1
# Imagem do frontend (Vue + Vite). Contexto de build: raiz do repositório.

FROM node:24.21.0-slim AS base
ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"
RUN npm install --global pnpm@12.9.1 && mkdir -p /app && chown node:node /app
WORKDIR /app
USER node

FROM base AS deps
COPY --chown=node:node frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Desenvolvimento: dependências na imagem, código montado como volume (hot reload).
FROM deps AS dev
EXPOSE 5173
CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]

FROM deps AS build
COPY --chown=node:node frontend/ ./
RUN pnpm exec vite build

# Produção: arquivos estáticos servidos pelo nginx com fallback de SPA.
FROM nginx:1.29-alpine AS production
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
