#!/bin/bash

# Build and tag Docker images for Kubernetes deployment

set -e

echo "Building Docker images..."

# Build backend image
echo "Building backend image..."
docker build -f Dockerfile.backend -t ldap-jwt-backend:latest .

# Build frontend image
echo "Building frontend image..."
docker build -f frontend/Dockerfile -t ldap-jwt-frontend:latest ./frontend

echo "Docker images built successfully!"

# Optional: Push to registry (uncomment and modify as needed)
# REGISTRY="your-registry.com"
# docker tag ldap-jwt-backend:latest $REGISTRY/ldap-jwt-backend:latest
# docker tag ldap-jwt-frontend:latest $REGISTRY/ldap-jwt-frontend:latest
# docker push $REGISTRY/ldap-jwt-backend:latest
# docker push $REGISTRY/ldap-jwt-frontend:latest

echo "Images ready for Kubernetes deployment!"
echo "Backend image: ldap-jwt-backend:latest"
echo "Frontend image: ldap-jwt-frontend:latest" 