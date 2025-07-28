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

echo "Applying networking and scaling..."
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/hpa.yaml

echo "Deploying NodePort services for external access..."
kubectl apply -f k8s/nodeport-services.yaml

echo "Deployment completed successfully!"

echo ""
echo "=== Deployment Status ==="
kubectl get pods -n ldap-jwt-app
echo ""
kubectl get services -n ldap-jwt-app

echo ""
echo "=== Access Information ==="
echo "Your application is accessible via NodePort services:"
echo ""
echo "Frontend: http://localhost:30080 or http://YOUR_IP:30080"
echo "Backend:  http://localhost:30800 or http://YOUR_IP:30800"
echo ""
echo "To find your IP address, run: ipconfig | findstr IPv4"
echo "Then access from any device on your network using your IP address." 