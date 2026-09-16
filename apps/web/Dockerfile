FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Production default: a real Next.js production build, not the dev server. The prior
# image ran `next dev` unconditionally (P2 — dev mode is slower, ships extra dev-only
# tooling, and is not the build meant to be exposed). docker-compose.yml overrides this
# CMD with `npm run dev` for local hot-reload, matching how apps/api/Dockerfile handles
# the same prod-image-vs-local-dev split.
RUN npm run build

# Unprivileged runtime user (P2 — the image previously ran as root, the default for the
# node:20-alpine base image when no USER is set).
RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
