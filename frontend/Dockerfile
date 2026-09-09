# syntax=docker/dockerfile:1
#
# Build stages run on the native runner platform (amd64) to avoid QEMU SIGILL
# crashes when Node.js runs npm ci under arm64 emulation. Only the final
# production stage targets linux/arm64 (the EC2 Graviton host).

FROM --platform=$BUILDPLATFORM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./

# Development
FROM base AS dev
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production build (runs natively on the CI runner — no QEMU involved)
FROM --platform=$BUILDPLATFORM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production runtime (arm64 — matches EC2 Graviton)
FROM node:20-alpine AS production
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "server.js"]
