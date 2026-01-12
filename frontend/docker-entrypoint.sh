#!/bin/sh
set -e

# Generate runtime config from environment variables
# Using envsubst to replace ${VAR} placeholders in the template

# Set defaults if not provided
export VITE_API_URL="${VITE_API_URL:-}"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-$VITE_API_URL}"
export VITE_OTEL_ENDPOINT="${VITE_OTEL_ENDPOINT:-/v1/traces}"
export VITE_SERVICE_NAME="${VITE_SERVICE_NAME:-batchivo-frontend}"
export VITE_SERVICE_VERSION="${VITE_SERVICE_VERSION:-1.0.0}"

# Generate config.js from template
envsubst < /usr/share/nginx/html/config.js.template > /usr/share/nginx/html/config.js

echo "Runtime config generated with VITE_API_URL=$VITE_API_URL"

# Execute the main command (nginx)
exec "$@"
