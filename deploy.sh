#!/bin/bash
set -e

# Nozzly Deployment Script for k3s
# This script builds Docker images and deploys to k3s cluster

echo "🚀 Nozzly Deployment Script"
echo "============================"
echo ""

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured or cluster is not reachable"
    exit 1
fi

echo "✅ Kubernetes cluster is reachable"
echo ""

# Step 1: Build Docker images
echo "📦 Building Docker images..."
echo ""

# Build backend
echo "Building backend image..."
cd backend
docker build -t nozzly-backend:latest .
echo "✅ Backend image built"
echo ""

# Build frontend
echo "Building frontend image..."
cd ../frontend
docker build -t nozzly-frontend:latest .
echo "✅ Frontend image built"
echo ""

cd ..

# Step 2: Load images into k3s (if using local k3s)
echo "📥 Loading images into k3s..."
echo ""

# For k3s, we can import images directly
if command -v k3s &> /dev/null; then
    echo "Importing images into k3s..."
    docker save nozzly-backend:latest | sudo k3s ctr images import -
    docker save nozzly-frontend:latest | sudo k3s ctr images import -
    echo "✅ Images loaded into k3s"
else
    echo "⚠️  k3s command not found - assuming images are in a registry"
fi
echo ""

# Step 3: Create namespace
echo "🏗️  Creating namespace..."
kubectl apply -f infrastructure/k8s/namespace/namespace.yaml
echo "✅ Namespace created"
echo ""

# Step 4: Deploy PostgreSQL
echo "🗄️  Deploying PostgreSQL..."
kubectl apply -f infrastructure/k8s/postgres/statefulset.yaml
echo "⏳ Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n nozzly --timeout=120s
echo "✅ PostgreSQL deployed and ready"
echo ""

# Step 5: Deploy Redis
echo "💾 Deploying Redis..."
kubectl apply -f infrastructure/k8s/redis/deployment.yaml
echo "⏳ Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n nozzly --timeout=60s
echo "✅ Redis deployed and ready"
echo ""

# Step 6: Deploy Backend
echo "⚙️  Deploying Backend..."
kubectl apply -f infrastructure/k8s/backend/deployment.yaml
echo "⏳ Waiting for backend to be ready..."
kubectl wait --for=condition=ready pod -l app=backend -n nozzly --timeout=120s
echo "✅ Backend deployed and ready"
echo ""

# Step 7: Deploy Frontend
echo "🎨 Deploying Frontend..."
kubectl apply -f infrastructure/k8s/frontend/deployment.yaml
echo "⏳ Waiting for frontend to be ready..."
kubectl wait --for=condition=ready pod -l app=frontend -n nozzly --timeout=120s
echo "✅ Frontend deployed and ready"
echo ""

# Step 8: Deploy Ingress
echo "🌐 Deploying Ingress..."
kubectl apply -f infrastructure/k8s/ingress/ingress.yaml
echo "✅ Ingress deployed"
echo ""

# Summary
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "Deployed components:"
echo "  ✅ PostgreSQL"
echo "  ✅ Redis"
echo "  ✅ Backend (2 replicas)"
echo "  ✅ Frontend (2 replicas)"
echo "  ✅ Ingress"
echo ""
echo "Check status with:"
echo "  kubectl get pods -n nozzly"
echo ""
echo "View logs with:"
echo "  kubectl logs -f deployment/backend -n nozzly"
echo "  kubectl logs -f deployment/frontend -n nozzly"
echo ""
echo "⚠️  Next steps:"
echo "  1. Configure Cloudflare Tunnel to point to your k3s ingress"
echo "  2. Update PostgreSQL password in infrastructure/k8s/postgres/statefulset.yaml"
echo "  3. Set up SSL certificates (if not using Cloudflare)"
echo ""
