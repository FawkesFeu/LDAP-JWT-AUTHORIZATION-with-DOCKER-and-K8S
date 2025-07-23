#!/bin/bash

# Clean up the LDAP JWT application from Kubernetes

set -e

echo "Cleaning up LDAP JWT application from Kubernetes..."

# Delete resources in reverse order
echo "Removing auto-scaling..."
kubectl delete -f k8s/hpa.yaml --ignore-not-found=true

echo "Removing networking..."
kubectl delete -f k8s/network-policy.yaml --ignore-not-found=true
kubectl delete -f k8s/ingress.yaml --ignore-not-found=true

echo "Removing frontend..."
kubectl delete -f k8s/frontend-deployment.yaml --ignore-not-found=true

echo "Removing backend..."
kubectl delete -f k8s/backend-deployment.yaml --ignore-not-found=true

echo "Removing LDAP server..."
kubectl delete -f k8s/ldap-deployment.yaml --ignore-not-found=true

echo "Removing Persistent Volumes..."
kubectl delete -f k8s/persistent-volume.yaml --ignore-not-found=true

echo "Removing ConfigMaps and Secrets..."
kubectl delete -f k8s/ldap-configmap.yaml --ignore-not-found=true
kubectl delete -f k8s/secrets.yaml --ignore-not-found=true
kubectl delete -f k8s/configmap.yaml --ignore-not-found=true

echo "Removing namespace..."
kubectl delete -f k8s/namespace.yaml --ignore-not-found=true

echo "Cleanup completed!"

# Optional: Remove persistent volume data
read -p "Do you want to remove persistent volume data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing persistent volume data..."
    sudo rm -rf /data/ldap-data
    sudo rm -rf /data/ldap-config
    echo "Persistent volume data removed."
fi 