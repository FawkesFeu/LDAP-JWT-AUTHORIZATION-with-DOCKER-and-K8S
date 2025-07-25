# LDAP JWT Authorization with Docker and Kubernetes

A comprehensive authentication system built with FastAPI backend, React frontend, and OpenLDAP, all deployed on Kubernetes with JWT-based authorization and role-based access control.

## 🚀 Quick Start

### Prerequisites

1. **Docker Desktop** (with Kubernetes enabled)
   - Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)
   - Enable Kubernetes: Settings → Kubernetes → ✅ Enable Kubernetes → Apply & Restart

2. **kubectl** (usually comes with Docker Desktop)
   ```powershell
   kubectl version --client
   ```

3. **Git** (to clone the repository)

### 🏃‍♂️ Setup Instructions

1. **Clone the repository**
   ```powershell
   git clone https://github.com/yourusername/LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S.git
   cd LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S
   ```

2. **Build Docker images**
   ```powershell
   # Build backend image
   docker build -f Dockerfile.backend -t ldap-jwt-backend:latest .
   
   # Build frontend image
   docker build -f frontend/Dockerfile -t ldap-jwt-frontend:latest ./frontend
   ```

3. **Deploy to Kubernetes**
   ```powershell
   # Create namespace and core resources
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/ldap-configmap.yaml
   kubectl apply -f k8s/frontend-nginx-config.yaml
   
   # Create storage
   kubectl apply -f k8s/persistent-volume.yaml
   
   # Deploy services
   kubectl apply -f k8s/ldap-deployment.yaml
   kubectl apply -f k8s/backend-deployment.yaml
   kubectl apply -f k8s/frontend-deployment.yaml
   
   # Setup networking
   kubectl apply -f k8s/ingress.yaml
   kubectl apply -f k8s/network-policy.yaml
   kubectl apply -f k8s/hpa.yaml
   ```

4. **Wait for pods to be ready**
   ```powershell
   # Check pod status (wait for all to show 1/1 or 2/2 Running)
   kubectl get pods -n ldap-jwt-app
   ```

5. **Setup LDAP users**
   ```powershell
   # Run the automated user setup script
   .\scripts\setup-ldap-users.ps1
   ```

6. **Access the application**
   - **Frontend**: http://localhost:30080
   - **Backend API**: http://localhost:30800

### 👥 Default User Accounts

| Username  | Password    | Role      | Employee ID |
|-----------|-------------|-----------|-------------|
| admin     | admin123    | admin     | ADMIN_01    |
| operator1 | operator123 | operator  | OP_01       |
| user1     | user123     | personnel | PER_01      |

## 🛠️ Development

### Architecture

- **Frontend**: React application with Tailwind CSS
- **Backend**: FastAPI with JWT authentication and LDAP integration
- **Database**: OpenLDAP server for user authentication
- **Deployment**: Kubernetes with auto-scaling and persistent storage

### Services Overview

- **LDAP Server**: Handles user authentication and authorization
- **Backend API**: JWT token generation, user management, role-based access
- **Frontend**: User interface for login and role-specific dashboards
- **Persistent Storage**: LDAP data persistence across pod restarts

## 🔧 Management Commands

### Monitoring
```powershell
# Check all pods
kubectl get pods -n ldap-jwt-app

# Check services
kubectl get services -n ldap-jwt-app

# View logs
kubectl logs deployment/backend-deployment -n ldap-jwt-app
kubectl logs deployment/frontend-deployment -n ldap-jwt-app
kubectl logs deployment/ldap-deployment -n ldap-jwt-app
```

### Scaling
```powershell
# Scale backend
kubectl scale deployment backend-deployment --replicas=3 -n ldap-jwt-app

# Scale frontend
kubectl scale deployment frontend-deployment --replicas=3 -n ldap-jwt-app
```

### Cleanup
```powershell
# Remove entire deployment
kubectl delete namespace ldap-jwt-app

# Or use cleanup script
.\scripts\cleanup.sh
```

## 🚨 Troubleshooting

### LDAP Connection Issues
If you get "401 Invalid Credentials" errors:

1. **Check LDAP pod status**
   ```powershell
   kubectl get pods -n ldap-jwt-app -l app=ldap
   ```

2. **Verify users exist**
   ```powershell
   kubectl exec deployment/ldap-deployment -n ldap-jwt-app -- ldapsearch -x -H ldap://localhost -D "cn=admin,dc=example,dc=com" -w admin -b "ou=users,dc=example,dc=com" "(objectClass=inetOrgPerson)"
   ```

3. **Re-run user setup**
   ```powershell
   .\scripts\setup-ldap-users.ps1
   ```

### Storage Issues
If LDAP pod is stuck in "Pending" status:

1. **Check storage class**
   ```powershell
   kubectl get storageclass
   ```

2. **Check persistent volumes**
   ```powershell
   kubectl get pvc -n ldap-jwt-app
   ```

3. **If using different storage class, update `k8s/persistent-volume.yaml`**

### Port Conflicts
If ports 30080 or 30800 are in use:
- Change NodePort values in `k8s/ingress.yaml`
- Restart the deployments

## 📁 Project Structure

```
├── backend/                 # FastAPI backend source
├── frontend/               # React frontend source
├── k8s/                   # Kubernetes manifests
├── ldap/                  # LDAP bootstrap data
├── scripts/               # Deployment and utility scripts
├── docker-compose.yml     # Local development with Docker Compose
├── Dockerfile.backend     # Backend container image
└── README.md             # This file
```

## 🔐 Security Features

- JWT-based authentication with role-based access control
- LDAP integration for centralized user management
- Network policies for pod-to-pod communication security
- Non-root container execution
- Persistent encrypted storage for LDAP data

## 📖 Additional Documentation

- [Kubernetes Deployment Guide](README-KUBERNETES.md)
- [Deployment Summary](DEPLOYMENT-SUMMARY.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the deployment
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. 