#!/bin/bash

# Deploy the LDAP JWT application to Kubernetes

set -e

echo "Deploying LDAP JWT application to Kubernetes..."

# Apply Kubernetes manifests in the correct order
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Creating ConfigMaps and Secrets..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/ldap-configmap.yaml
kubectl apply -f k8s/frontend-nginx-config.yaml

echo "Creating Persistent Volumes..."
kubectl apply -f k8s/persistent-volume.yaml

echo "Deploying LDAP server..."
kubectl apply -f k8s/ldap-deployment.yaml

echo "Waiting for LDAP server to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ldap-deployment -n ldap-jwt-app

echo "Deploying backend..."
kubectl apply -f k8s/backend-deployment.yaml

echo "Waiting for backend to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend-deployment -n ldap-jwt-app

echo "Deploying frontend..."
kubectl apply -f k8s/frontend-deployment.yaml

echo "Waiting for frontend to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/frontend-deployment -n ldap-jwt-app

echo "Applying networking..."
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/network-policy.yaml

echo "Applying auto-scaling..."
kubectl apply -f k8s/hpa.yaml

echo "Deployment completed successfully!"

echo ""
echo "=== Deployment Status ==="
kubectl get pods -n ldap-jwt-app
echo ""
kubectl get services -n ldap-jwt-app
echo ""
kubectl get ingress -n ldap-jwt-app

echo ""
echo "=== Access Information ==="
echo "If using NodePort services:"
echo "Frontend: http://localhost:30080"
echo "Backend:  http://localhost:30800"
echo ""
echo "If using Ingress:"
echo "Add '127.0.0.1 ldap-jwt-app.local' to your /etc/hosts file"
echo "Then access: http://ldap-jwt-app.local" 