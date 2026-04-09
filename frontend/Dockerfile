FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* frontend/tsconfig.json frontend/next-env.d.ts frontend/next.config.ts /app/
RUN npm ci

COPY frontend/app /app/app
COPY frontend/components /app/components
COPY frontend/lib /app/lib
COPY frontend/public /app/public

RUN npm run build

FROM node:22-alpine AS runner

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

WORKDIR /app

COPY --from=builder /app/.next/standalone /app
COPY --from=builder /app/.next/static /app/.next/static
COPY --from=builder /app/public /app/public

EXPOSE 3000

CMD ["node", "server.js"]
