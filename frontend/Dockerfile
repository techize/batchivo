# Multi-stage Dockerfile for React frontend with Vite

# Stage 1: Builder
FROM node:25-alpine as builder

WORKDIR /app

# Build arguments for Vite environment variables
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Copy dependency files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application (Vite embeds env vars at build time)
RUN npm run build

# Stage 2: Runtime with nginx
FROM nginx:1.27-alpine

# Update system packages to patch vulnerabilities (CVE-2025-49794, CVE-2025-49796)
RUN apk upgrade --no-cache

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user and set up permissions
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chmod -R 755 /var/cache/nginx /var/log/nginx

USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
