# Dockerfile — Binance OHLC Pipeline (TypeScript)
# Multi-stage: build TS -> runtime node slim senza devDependencies.
# Uso:
#   docker build -t ohlc-pipeline .
#   docker run --rm --env-file .env -v %cd%/data:/app/data ohlc-pipeline

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:20-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
# .env montato a runtime; data come volume
VOLUME ["/app/data"]
CMD ["node", "dist/index.js"]
