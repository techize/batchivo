#!/bin/bash
# Setup secrets for batchivo-staging namespace
# Run this script once after creating the namespace
#
# Prerequisites:
# - kubectl configured for cluster access
# - batchivo-staging namespace exists
# - Access to production secrets for reference

set -e

NAMESPACE="batchivo-staging"

echo "Setting up secrets for $NAMESPACE..."

# Check namespace exists
if ! kubectl get namespace $NAMESPACE &>/dev/null; then
    echo "Error: Namespace $NAMESPACE does not exist"
    echo "Run: kubectl apply -f namespace.yaml"
    exit 1
fi

# PostgreSQL credentials (copy from production - same user, different DB)
echo "Creating postgres-secret..."
POSTGRES_USER=$(kubectl get secret postgres-secret -n batchivo -o jsonpath='{.data.POSTGRES_USER}' | base64 -d)
POSTGRES_PASSWORD=$(kubectl get secret postgres-secret -n batchivo -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)

kubectl create secret generic postgres-secret -n $NAMESPACE \
    --from-literal=POSTGRES_USER="$POSTGRES_USER" \
    --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -

# MinIO credentials (copy from production - shared MinIO)
echo "Creating minio-credentials..."
MINIO_USER=$(kubectl get secret minio-credentials -n batchivo -o jsonpath='{.data.MINIO_ROOT_USER}' | base64 -d)
MINIO_PASSWORD=$(kubectl get secret minio-credentials -n batchivo -o jsonpath='{.data.MINIO_ROOT_PASSWORD}' | base64 -d)

kubectl create secret generic minio-credentials -n $NAMESPACE \
    --from-literal=MINIO_ROOT_USER="$MINIO_USER" \
    --from-literal=MINIO_ROOT_PASSWORD="$MINIO_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -

# Backend secrets (generate new for staging)
echo "Creating backend-secrets..."
SECRET_KEY=$(openssl rand -hex 32)

kubectl create secret generic backend-secrets -n $NAMESPACE \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

# Harbor registry credentials (copy from production)
echo "Creating harbor-creds..."
kubectl get secret harbor-creds -n batchivo -o yaml | \
    sed "s/namespace: batchivo/namespace: $NAMESPACE/" | \
    kubectl apply -f -

echo ""
echo "✓ Core secrets created!"
echo ""
echo "Optional secrets (create manually if needed):"
echo "  - square-credentials (use Square sandbox keys)"
echo "  - resend-credentials (for email testing)"
echo ""
echo "To create Square sandbox credentials:"
echo "  kubectl create secret generic square-credentials -n $NAMESPACE \\"
echo "    --from-literal=SQUARE_ACCESS_TOKEN=<sandbox-token> \\"
echo "    --from-literal=SQUARE_ENVIRONMENT=sandbox \\"
echo "    --from-literal=SQUARE_APPLICATION_ID=<sandbox-app-id> \\"
echo "    --from-literal=SQUARE_LOCATION_ID=<sandbox-location-id>"
