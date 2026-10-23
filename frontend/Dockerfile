# Фронтенд: Next.js standalone (ADR-0011). Образ собирает CI, VPS только скачивает его.
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# Нужен на этапе сборки: из него строятся абсолютные ссылки og:image для превью в соцсетях.
ARG PUBLIC_ORIGIN=https://karrad.tech
ENV PUBLIC_ORIGIN=$PUBLIC_ORIGIN
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 \
    NODE_OPTIONS=--max-old-space-size=128
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /app/.next/standalone ./
COPY --from=build --chown=app:app /app/.next/static ./.next/static
COPY --from=build --chown=app:app /app/public ./public
USER app
EXPOSE 3000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 \
  CMD wget -qO /dev/null http://127.0.0.1:3000/studlenta || exit 1
CMD ["node", "server.js"]
