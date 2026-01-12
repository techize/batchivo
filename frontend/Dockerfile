# Multi-stage Dockerfile for React frontend with Vite

# Stage 1: Builder
FROM node:20-alpine as builder

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
FROM nginx:1.29-alpine

# Update system packages and install envsubst (from gettext)
RUN apk upgrade --no-cache && \
    apk add --no-cache gettext

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy config template (entrypoint will generate config.js from this)
COPY public/config.js.template /usr/share/nginx/html/config.js.template

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

# Use entrypoint to generate runtime config, then run nginx
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
