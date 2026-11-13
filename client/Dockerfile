# Production image: builds the web app, then serves it with Caddy, which also
# gets and renews the HTTPS certificate and forwards /api to the API container.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml .npmrc ./
# pnpm is pinned: newer major versions refuse to install until every package
# with a build script (esbuild) is approved, which broke this step.
RUN npm install -g pnpm@9 && pnpm install --frozen-lockfile
COPY . .
# Same origin as the site, so no CORS and the login cookie just works
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
