# API de leads (Node 20, sin dependencias). Contexto de build: raíz del repo.
FROM node:20-alpine
WORKDIR /srv
COPY functions/_lib ./functions/_lib
COPY api/server.mjs ./api/server.mjs
ENV NODE_ENV=production PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health >/dev/null || exit 1
USER node
CMD ["node", "api/server.mjs"]
