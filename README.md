# LDAP JWT Authentication System

> Secure LDAP authentication system with JWT/JWE encryption and role-based access control. React frontend + FastAPI backend deployed on Kubernetes with Docker.

![Tech Stack](https://img.shields.io/badge/React-18.2.0-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg)
![LDAP](https://img.shields.io/badge/OpenLDAP-1.5.0-orange.svg)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React         │    │   FastAPI        │    │   OpenLDAP      │
│   Frontend      │───▶│   Backend        │───▶│   Server        │
│   (Port 30080)  │    │   (Port 30800)   │    │   (Port 389)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ frontend-service│    │ backend-service  │    │  ldap-service   │
│   ClusterIP     │    │   ClusterIP      │    │   ClusterIP     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Kubernetes Ingress                            │
│            (Routes /api/ to backend, / to frontend)             │
└──────────────────────────────────────────────────────────────────┘
```

## ✨ Features

- 🔐 **Secure Authentication**: LDAP-based user authentication with encrypted JWT/JWE tokens
- 🎭 **Role-Based Access Control**: Three user roles with different permissions
  - **Admin**: Full system access, user management
  - **Operator**: Can view and manage personnel users
  - **Personnel**: Basic user access, can view operator count
- 🚀 **Modern Tech Stack**: React 18 + FastAPI + OpenLDAP
- 📦 **Kubernetes Ready**: Complete Kubernetes deployment with auto-scaling
- 🛡️ **Security Features**: 
  - JWT/JWE token encryption
  - CORS protection
  - Network policies
  - Non-root containers
- 📊 **Monitoring**: Health checks, liveness/readiness probes
- 🔄 **Auto-scaling**: Horizontal Pod Autoscaler (HPA) based on CPU/memory

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Frontend** | React | 18.2.0 |
| **Backend** | FastAPI | 0.104.1 |
| **Authentication** | OpenLDAP | 1.5.0 |
| **Database** | LDAP Directory | - |
| **Containerization** | Docker | Latest |
| **Orchestration** | Kubernetes | 1.20+ |
| **Web Server** | Nginx | Alpine |
| **Security** | JWT + JWE | - |

## 📋 Prerequisites

- **Docker Desktop** with Kubernetes enabled
- **kubectl** CLI tool
- **Node.js** 18+ (for development)
- **Python** 3.11+ (for development)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ldap_jwt_pts_kubernetes_trial
```

### 2. Build Docker Images
```bash
# Build backend
docker build -f Dockerfile.backend -t ldap-jwt-backend:latest .

# Build frontend  
docker build -f frontend/Dockerfile -t ldap-jwt-frontend:latest ./frontend
```

### 3. Deploy to Kubernetes
```bash
# Create namespace and configuration
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

### 4. Access the Application
- **Frontend**: http://localhost:30080
- **Backend API**: http://localhost:30800/docs

## 👥 Default Users

| Username | Password | Role | Employee ID | Permissions |
|----------|----------|------|-------------|-------------|
| `admin` | `admin123` | admin | ADMIN_01 | Full system access, user management |
| `operator1` | `operator123` | operator | OP_01 | View/manage personnel users |
| `user1` | `user123` | personnel | PER_01 | Basic access, view operator count |

## 🔧 Configuration

### Environment Variables

#### Backend Configuration
```yaml
LDAP_SERVER: "ldap://ldap-service:389"
LDAP_BASE_DN: "ou=users,dc=example,dc=com"
LDAP_ADMIN_DN: "cn=admin,dc=example,dc=com"
LDAP_ADMIN_PASS: "admin"
JWE_SECRET_KEY: "your-32-character-secret-key"
```

#### Frontend Configuration
```yaml
REACT_APP_BACKEND_URL: "http://localhost:30800"
```

### Customizing LDAP Users
Edit `k8s/ldap-configmap.yaml` to add/modify users:

```yaml
data:
  02-users.ldif: |
    dn: uid=newuser,ou=users,dc=example,dc=com
    objectClass: top
    objectClass: inetOrgPerson
    uid: newuser
    cn: New User
    sn: User
    userPassword: password123
    employeeType: personnel
    employeeNumber: PER_02
```

## 📖 API Documentation

### Authentication Endpoints
- `POST /login` - User login
- `POST /verify-token` - Token verification

### Admin Endpoints (Admin role required)
- `GET /admin/users` - List all users
- `POST /admin/create-user` - Create new user
- `POST /admin/reset-password` - Reset user password
- `POST /admin/change-role` - Change user role
- `POST /admin/delete-user` - Delete user

### User Endpoints
- `GET /users/me` - Get current user info
- `GET /users/for-operator` - List personnel (Operator role)
- `GET /users/operator-count` - Get operator count (Personnel role)

### Example API Usage
```bash
# Login
curl -X POST "http://localhost:30800/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# Create user (Admin only)
curl -X POST "http://localhost:30800/admin/create-user" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=newuser&password=pass123&name=New User&role=personnel"
```

## 🎮 Usage Guide

### Admin Dashboard
1. Login with admin credentials
2. Access admin dashboard from protected page
3. Manage users: create, delete, reset passwords, change roles
4. View all system users and their details

### Operator Features
1. Login with operator credentials
2. Access team view to see personnel users
3. Monitor personnel list and their employee IDs

### Personnel Features  
1. Login with personnel credentials
2. View current operator count in the system
3. Access user profile information

## 🔄 Server Management

### Start/Stop Server
```bash
# Stop all services
kubectl scale deployment --all --replicas=0 -n ldap-jwt-app

# Start services (in order)
kubectl scale deployment ldap-deployment --replicas=1 -n ldap-jwt-app
kubectl scale deployment backend-deployment --replicas=2 -n ldap-jwt-app
kubectl scale deployment frontend-deployment --replicas=2 -n ldap-jwt-app

# Check status
kubectl get pods -n ldap-jwt-app
```

### Monitoring
```bash
# Check pod status
kubectl get pods -n ldap-jwt-app

# View logs
kubectl logs -f deployment/backend-deployment -n ldap-jwt-app
kubectl logs -f deployment/frontend-deployment -n ldap-jwt-app
kubectl logs -f deployment/ldap-deployment -n ldap-jwt-app

# Check services
kubectl get services -n ldap-jwt-app

# Monitor resource usage
kubectl top pods -n ldap-jwt-app
```

## 🧪 Development

### Local Development Setup
```bash
# Backend development
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd frontend
npm install
npm start
```

### Building Custom Images
```bash
# Frontend with custom backend URL
cd frontend
REACT_APP_BACKEND_URL=http://your-backend-url npm run build
cd ..
docker build -f frontend/Dockerfile -t ldap-jwt-frontend:custom ./frontend

# Backend with custom settings
docker build -f Dockerfile.backend -t ldap-jwt-backend:custom .
```

## 🐛 Troubleshooting

### Common Issues

#### Pods in CrashLoopBackOff
```bash
# Check pod logs
kubectl logs <pod-name> -n ldap-jwt-app

# Check pod description
kubectl describe pod <pod-name> -n ldap-jwt-app
```

#### CORS Errors
```bash
# Update CORS origins in backend
kubectl patch configmap app-config -n ldap-jwt-app -p '{"data":{"CORS_ORIGINS":"http://localhost:30080,http://localhost:3000"}}'
kubectl rollout restart deployment/backend-deployment -n ldap-jwt-app
```

#### Image Pull Errors
```bash
# Use local images
kubectl patch deployment <deployment-name> -n ldap-jwt-app -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","imagePullPolicy":"IfNotPresent"}]}}}}'
```

#### LDAP Connection Issues
```bash
# Check LDAP logs
kubectl logs -f deployment/ldap-deployment -n ldap-jwt-app

# Test LDAP connection
kubectl exec -it deployment/ldap-deployment -n ldap-jwt-app -- ldapsearch -x -D "cn=admin,dc=example,dc=com" -w admin -b "dc=example,dc=com"
```

### Debug Commands
```bash
# Port forward for local testing
kubectl port-forward service/frontend-service 3000:80 -n ldap-jwt-app
kubectl port-forward service/backend-service 8000:8000 -n ldap-jwt-app

# Get into containers
kubectl exec -it deployment/backend-deployment -n ldap-jwt-app -- /bin/bash
kubectl exec -it deployment/frontend-deployment -n ldap-jwt-app -- /bin/sh
```

## 🌐 Making Server Public

### Using ngrok (Free)
```bash
# Install ngrok and expose services
ngrok http 30080  # Frontend
ngrok http 30800  # Backend (in another terminal)
```

### Cloud Deployment
- **AWS EKS**: $72/month + instances
- **Azure AKS**: Free control plane + instances
- **Google GKE**: Free small clusters + instances
- **DigitalOcean**: $12/month + nodes

## 🔒 Security Considerations

### Production Checklist
- [ ] Change default LDAP admin password
- [ ] Update JWT secret key (32+ characters)
- [ ] Configure HTTPS/TLS certificates  
- [ ] Set up proper CORS origins
- [ ] Enable network policies
- [ ] Configure resource limits
- [ ] Set up backup for LDAP data
- [ ] Monitor logs and metrics
- [ ] Use secrets management (Vault, etc.)

### Security Features
- Non-root containers
- Network policies between services
- Encrypted JWT/JWE tokens
- LDAP authentication
- Role-based access control
- Health checks and monitoring

## 📁 Project Structure

```
ldap_jwt_pts_kubernetes_trial/
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── persistent-volume.yaml
│   ├── ldap-deployment.yaml
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── ingress.yaml
│   ├── network-policy.yaml
│   └── hpa.yaml
├── scripts/                    # Deployment scripts
│   ├── build-images.sh
│   ├── deploy.sh
│   └── cleanup.sh
├── frontend/                   # React application
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── ldap/                       # LDAP configuration
│   ├── 01-organizational-unit.ldif
│   └── 02-users.ldif
├── main.py                     # FastAPI backend
├── requirements.txt            # Python dependencies
├── Dockerfile.backend          # Backend Docker image
├── docker-compose.yml          # Local development
└── README.md                   # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenLDAP for directory services
- FastAPI for the excellent Python web framework
- React team for the frontend framework
- Kubernetes community for orchestration tools

---

**Built with ❤️ using React, FastAPI, and Kubernetes** 