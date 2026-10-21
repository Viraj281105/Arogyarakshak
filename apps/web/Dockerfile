# syntax=docker/dockerfile:1
# ArogyaRakshak web image (Next.js). Build context: ./apps/web.
#
# NEXT_PUBLIC_API_URL is inlined into the browser bundle at BUILD time; pass it as a
# build arg for anything other than the local default (http://localhost:8000).

# ── build ──────────────────────────────────────────────────────────────────────────────
# Also the target `docker compose` uses for `next dev` (full source + dev dependencies).
FROM node:20-alpine AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build \
    && npm prune --omit=dev

# ── runtime ────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Unprivileged runtime user; the app files stay root-owned and read-only to it. Next.js
# only writes its image/ISR cache under .next/cache, which is made writable.
RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app app

COPY --from=build /app/package.json /app/package-lock.json ./
# Dev dependencies are not pruned yet: next.config.ts is loaded at start-up and pruning
# has not been verified against it in a running container. Measure before shrinking.
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/next.config.ts ./next.config.ts
RUN mkdir -p .next/cache && chown -R app:app .next/cache

USER app
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

# Production build. docker-compose.yml overrides this with `npm run dev` for hot reload.
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
