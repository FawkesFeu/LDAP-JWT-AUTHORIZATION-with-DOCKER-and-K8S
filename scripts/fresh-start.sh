#!/bin/bash

set -euo pipefail

echo "Starting fresh deployment (Linux) with data preservation..."

# 1. Optional cleanup (keeps data if PVs use hostPath Retain)
echo "[1/6] Cleaning up previous resources (namespace will be recreated)"
kubectl delete namespace ldap-jwt-app --ignore-not-found=true || true
sleep 3

# 2. Build Docker images (requires Docker or podman compatible setup)
echo "[2/6] Building Docker images..."
docker build -f Dockerfile.backend -t ldap-jwt-backend:latest .
docker build -f frontend/Dockerfile -t ldap-jwt-frontend:latest ./frontend

# 3. Deploy Kubernetes resources
echo "[3/6] Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/persistent-volume.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/ldap-configmap.yaml
kubectl apply -f k8s/frontend-nginx-config.yaml

echo "[3.1] Deploying TimescaleDB (database)..."
kubectl apply -f k8s/timescaledb-init-configmap.yaml
kubectl apply -f k8s/timescaledb-deployment.yaml

echo "Waiting for TimescaleDB to be ready..."
kubectl wait --for=condition=ready pod -l app=timescaledb -n ldap-jwt-app --timeout=300s

echo "[3.2] Initializing database schema..."
kubectl apply -f k8s/database-init-job.yaml
kubectl wait --for=condition=complete job/database-init-job -n ldap-jwt-app --timeout=300s

echo "[3.3] Running migration and population jobs..."
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/user-migration-job -n ldap-jwt-app --timeout=300s
kubectl apply -f k8s/populate-tables-job.yaml
kubectl wait --for=condition=complete job/populate-tables-job -n ldap-jwt-app --timeout=300s

echo "[3.4] Deploying LDAP server..."
kubectl apply -f k8s/ldap-deployment.yaml
kubectl wait --for=condition=available --timeout=300s deployment/ldap-deployment -n ldap-jwt-app

echo "[3.5] Deploying backend..."
kubectl apply -f k8s/backend-deployment.yaml
kubectl wait --for=condition=available --timeout=300s deployment/backend-deployment -n ldap-jwt-app

echo "[3.6] Deploying frontend..."
kubectl apply -f k8s/frontend-deployment.yaml
kubectl wait --for=condition=available --timeout=300s deployment/frontend-deployment -n ldap-jwt-app

echo "[3.7] Networking and scaling..."
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/nodeport-services.yaml

# 4. Verify
echo "[4/6] Deployment status:"
kubectl get pods -n ldap-jwt-app
kubectl get services -n ldap-jwt-app

# 5. Access information
echo "[5/6] Access Information:"
echo "Frontend: http://localhost:30080"
echo "Backend:  http://localhost:30800"

echo "[6/6] Done."


