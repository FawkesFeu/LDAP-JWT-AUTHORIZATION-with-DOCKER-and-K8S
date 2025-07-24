# 🚀 Quick Start Guide

## Prerequisites ✅
- Docker Desktop with Kubernetes enabled
- Git installed

## One-Time Setup Commands 📋

```powershell
# 1. Clone repository
git clone https://github.com/yourusername/LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S.git
cd LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S

# 2. Build images
docker build -f Dockerfile.backend -t ldap-jwt-backend:latest .
docker build -f frontend/Dockerfile -t ldap-jwt-frontend:latest ./frontend

# 3. Deploy everything
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/ldap-configmap.yaml
kubectl apply -f k8s/frontend-nginx-config.yaml
kubectl apply -f k8s/persistent-volume.yaml
kubectl apply -f k8s/ldap-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/hpa.yaml

# 4. Wait for pods to be ready
kubectl get pods -n ldap-jwt-app

# 5. Setup users (wait for LDAP pod to be 1/1 Running first)
.\scripts\setup-ldap-users.ps1
```

## Access Your Application 🌐
- **Frontend**: http://localhost:30080
- **Backend API**: http://localhost:30800

## Login Credentials 👥
- **admin** / admin123 (admin role)
- **operator1** / operator123 (operator role)  
- **user1** / user123 (personnel role)

## Useful Commands 🔧

```powershell
# Check status
kubectl get pods -n ldap-jwt-app

# View logs
kubectl logs deployment/backend-deployment -n ldap-jwt-app
kubectl logs deployment/ldap-deployment -n ldap-jwt-app

# Restart services
kubectl rollout restart deployment/backend-deployment -n ldap-jwt-app

# Complete cleanup
kubectl delete namespace ldap-jwt-app

# Re-setup users (if needed)
.\scripts\setup-ldap-users.ps1
```

## Troubleshooting 🚨
- **401 errors**: Run `.\scripts\setup-ldap-users.ps1`
- **Pods pending**: Check `kubectl get pvc -n ldap-jwt-app`
- **Can't access**: Verify Docker Desktop Kubernetes is enabled

That's it! 🎉 