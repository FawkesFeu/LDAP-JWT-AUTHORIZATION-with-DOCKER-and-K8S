# LDAP JWT Application - Kubernetes Deployment

This guide provides instructions for deploying the LDAP JWT application to Kubernetes.

## Architecture

The application consists of three main components:

1. **LDAP Server**: OpenLDAP server for user authentication
2. **Backend API**: FastAPI application with JWT authentication and role-based access control
3. **Frontend**: React application served by Nginx

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured to access your cluster
- Docker for building images
- NGINX Ingress Controller (optional, for Ingress-based access)

## Quick Start

### 1. Build Docker Images

```bash
chmod +x scripts/build-images.sh
./scripts/build-images.sh
```

### 2. Deploy to Kubernetes

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. Access the Application

#### Option A: Using NodePort Services
- Frontend: http://localhost:30080
- Backend API: http://localhost:30800

#### Option B: Using Ingress (if NGINX Ingress Controller is installed)
1. Add to your `/etc/hosts` file:
   ```
   127.0.0.1 ldap-jwt-app.local
   ```
2. Access: http://ldap-jwt-app.local

## Default Users

The application comes with three pre-configured users:

| Username  | Password    | Role      | Employee ID |
|-----------|-------------|-----------|-------------|
| admin     | admin123    | admin     | ADMIN_01    |
| operator1 | operator123 | operator  | OP_01       |
| user1     | user123     | personnel | PER_01      |

## Kubernetes Resources

### Core Resources
- **Namespace**: `ldap-jwt-app`
- **ConfigMaps**: Application configuration
- **Secrets**: Sensitive data (passwords, JWT keys)
- **PersistentVolumes**: LDAP data storage

### Deployments
- **LDAP Deployment**: Single replica with persistent storage
- **Backend Deployment**: 2 replicas with auto-scaling
- **Frontend Deployment**: 2 replicas with auto-scaling

### Networking
- **Services**: Internal communication between components
- **Ingress**: External access routing
- **NetworkPolicies**: Security isolation between components

### Auto-scaling
- **HorizontalPodAutoscaler**: Automatic scaling based on CPU/memory usage
  - Backend: 2-10 replicas
  - Frontend: 2-5 replicas

## Manual Deployment Steps

If you prefer to deploy manually:

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create configuration
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml  
kubectl apply -f k8s/ldap-configmap.yaml
kubectl apply -f k8s/frontend-nginx-config.yaml

# 3. Create storage
kubectl apply -f k8s/persistent-volume.yaml

# 4. Deploy services
kubectl apply -f k8s/ldap-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# 5. Setup networking
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/network-policy.yaml

# 6. Enable auto-scaling
kubectl apply -f k8s/hpa.yaml
```

## Monitoring

Check deployment status:

```bash
# Check pods
kubectl get pods -n ldap-jwt-app

# Check services
kubectl get services -n ldap-jwt-app

# Check ingress
kubectl get ingress -n ldap-jwt-app

# Check logs
kubectl logs -f deployment/backend-deployment -n ldap-jwt-app
kubectl logs -f deployment/frontend-deployment -n ldap-jwt-app
kubectl logs -f deployment/ldap-deployment -n ldap-jwt-app
```

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending state**
   - Check persistent volume availability
   - Verify node resources (CPU/memory)

2. **LDAP connection issues**
   - Check LDAP pod logs: `kubectl logs -f deployment/ldap-deployment -n ldap-jwt-app`
   - Verify service discovery: `kubectl get svc -n ldap-jwt-app`

3. **Backend API errors**
   - Check backend logs for LDAP connection errors
   - Verify ConfigMap and Secret values

4. **Frontend not loading**
   - Check nginx configuration
   - Verify backend service connectivity

### Debug Commands

```bash
# Get into a pod for debugging
kubectl exec -it deployment/backend-deployment -n ldap-jwt-app -- /bin/bash

# Port forward for local testing
kubectl port-forward service/frontend-service 3000:80 -n ldap-jwt-app
kubectl port-forward service/backend-service 8000:8000 -n ldap-jwt-app

# Check resource usage
kubectl top pods -n ldap-jwt-app
```

## Scaling

### Manual Scaling
```bash
# Scale backend
kubectl scale deployment backend-deployment --replicas=5 -n ldap-jwt-app

# Scale frontend  
kubectl scale deployment frontend-deployment --replicas=3 -n ldap-jwt-app
```

### Auto-scaling Configuration
The HPA automatically scales based on:
- CPU utilization (70% threshold)
- Memory utilization (80% threshold for backend)

## Security Features

- **Network Policies**: Restrict communication between pods
- **Secrets**: Encrypted storage of sensitive data
- **Non-root Containers**: All containers run as non-root users
- **Resource Limits**: Prevent resource exhaustion
- **Health Checks**: Liveness and readiness probes

## Customization

### Environment Variables
Modify `k8s/configmap.yaml` and `k8s/secrets.yaml` for your environment:

- LDAP domain and organization
- JWT secret key
- Backend/frontend URLs
- User roles and permissions

### Persistent Storage
The default configuration uses `hostPath` volumes. For production:

1. Use proper storage classes (AWS EBS, GCE PD, etc.)
2. Configure backup strategies
3. Set appropriate retention policies

### Image Registry
For production deployments, push images to a container registry:

```bash
# Tag and push images
docker tag ldap-jwt-backend:latest your-registry.com/ldap-jwt-backend:v1.0.0
docker tag ldap-jwt-frontend:latest your-registry.com/ldap-jwt-frontend:v1.0.0

docker push your-registry.com/ldap-jwt-backend:v1.0.0
docker push your-registry.com/ldap-jwt-frontend:v1.0.0

# Update deployment manifests with registry URLs
```

## Cleanup

To remove the entire deployment:

```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh
```

This will remove all Kubernetes resources and optionally clean up persistent volume data.

## Production Recommendations

1. **Use a container registry** for image storage
2. **Configure proper persistent storage** with backup
3. **Set up monitoring** (Prometheus/Grafana)
4. **Configure logging** (ELK stack or similar)
5. **Use TLS/SSL certificates** for secure communication
6. **Implement resource quotas** and limits
7. **Set up backup strategies** for LDAP data
8. **Configure network policies** for security
9. **Use secrets management** (Vault, sealed-secrets)
10. **Implement GitOps** for deployment automation 