FROM node:20-alpine AS base

WORKDIR /app
COPY package*.json ./

# Development
FROM base AS dev
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production build
FROM base AS builder
RUN npm ci
COPY . .
RUN npm run build

# Production runtime
FROM node:20-alpine AS production
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "server.js"]
