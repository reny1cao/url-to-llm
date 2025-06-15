# Frontend Dockerfile optimized for Cloud Run
FROM node:18-alpine AS deps
WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml* package-lock.json* yarn.lock* ./
RUN \
  if [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install --frozen-lockfile; \
  elif [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  else echo "No lockfile found." && npm install; \
  fi

# Build stage
FROM node:18-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for API URL
ARG NEXT_PUBLIC_API_URL=https://url-to-llm-857813849242.asia-southeast1.run.app
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Build the application
RUN \
  if [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm build; \
  elif [ -f yarn.lock ]; then yarn build; \
  else npm run build; \
  fi

# Production stage
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Copy necessary files
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# Standalone build for Cloud Run
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Cloud Run port
ENV PORT 8080
EXPOSE 8080

ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]