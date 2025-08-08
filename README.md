# LDAP JWT Authorization with Kubernetes

A comprehensive authentication system built with FastAPI backend, React frontend, and OpenLDAP, all deployed on Kubernetes with JWT-based authorization, role-based access control, and persistent user data storage.

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

### 🏃‍♂️ One-Command Deployment

```powershell
# Clone and deploy everything in one go
git clone https://github.com/yourusername/LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S.git
cd LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S
.\fresh-start.ps1
```

### 📋 Manual Setup Instructions

1. **Clone the repository**
   ```powershell
   git clone https://github.com/yourusername/LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S.git
   cd LDAP-JWT-AUTHORAZATION-with-DOCKER-and-K8S
   ```

2. **Create required directories** (if they don't exist)
   ```powershell
   # Create directories for persistent LDAP data
   New-Item -ItemType Directory -Path "C:\ldap-data" -Force
   New-Item -ItemType Directory -Path "C:\ldap-config" -Force
   ```

3. **Deploy with fresh start script**
   ```powershell
   .\fresh-start.ps1
   ```

4. **Access your application**
   - **Frontend**: http://localhost:30080 or http://YOUR_IP:30080
   - **Backend API**: http://localhost:30800 or http://YOUR_IP:30800

### 👥 Default User Accounts

| Username  | Password    | Role      | Employee ID | Access Level |
|-----------|-------------|-----------|-------------|--------------|
| admin     | admin123    | admin     | ADMIN_01    | Full admin access |
| operator1 | operator123 | operator  | OP_01       | Can view personnel users |
| user1     | user123     | personnel | PER_01      | Basic user access |

## 🛠️ Architecture & Technologies

### **Core Application Stack:**
- **Backend**: 
  - **FastAPI** (Python 3.11) with **Uvicorn** ASGI server
  - **PyJWT** for JWT token handling
  - **Cryptography** for encryption/decryption
  - **python-ldap3** for LDAP client operations
  - **TimescaleDB/PostgreSQL** for metadata storage (login attempts, user metadata, sessions, lockouts, admin audit)

- **Frontend**:
  - **React 19** with **Tailwind CSS**
  - **Nginx** web server for production serving
  - **Axios** for HTTP client communication
  - **React Router DOM** for client-side routing

- **Database/Directory**:
  - **OpenLDAP** server for centralized user authentication
  - **LDAP protocol** for secure authentication

### **Infrastructure & Deployment:**
- **Docker** for containerization
- **Kubernetes** for orchestration with:
  - **Deployments** for pod management
  - **Services** for networking (ClusterIP + NodePort)
  - **ConfigMaps** for configuration management
  - **Secrets** for sensitive data encryption
  - **PersistentVolumes** for data persistence (LDAP + TimescaleDB)
  - **HorizontalPodAutoscaler** for auto-scaling
  - **NetworkPolicies** for security isolation

### **Database Components:**
- StatefulSet `timescaledb-statefulset` exposes `timescaledb-service:5432`
- Initialization via `k8s/timescaledb-init-configmap.yaml` (tables, indexes, functions)
- DB credentials from `k8s/secrets.yaml` (DB_USER, DB_PASSWORD)
- DB used by backend for:
  - Recording login attempts and lockouts
  - Persisting refresh tokens (`jwt_sessions`)
  - Storing user metadata (role, authorization_level, persistent employee_id)
  - Admin actions audit log (`admin_actions`)

### **Persistent Data Storage:**
- PersistentVolumes use Docker Desktop host mounts (portable on Windows):
  - `/run/desktop/mnt/host/c/ldap-data` (maps to `C:\\ldap-data` on the host)
  - `/run/desktop/mnt/host/c/ldap-config` (maps to `C:\\ldap-config` on the host)
- On Linux/macOS, update only the `hostPath.path` values in `k8s/persistent-volume.yaml` to directories you create on the node (e.g., `/srv/ldap-data`, `/srv/ldap-config`).
- Manual storage class is set to retain data across fresh deployments.

## 🔧 Management Scripts

### **Fresh Start (Preserves User Data)**
```powershell
.\fresh-start.ps1
```
- Builds Docker images
- Deploys entire Kubernetes stack
- Preserves existing user data
- Shows access URLs and credentials

### **Cleanup (Preserves User Data)**
```powershell
.\scripts\cleanup-keep-data.ps1
```
- Removes Kubernetes deployment
- Preserves LDAP user data
- Cleans up Docker containers

### **Complete Shutdown**
```powershell
.\shutdown.ps1
```
- Stops all containers
- Removes all Kubernetes resources
- Optional Docker system cleanup
- Complete system shutdown

## 🌐 Network Access

### **Local Access:**
- **Frontend**: http://localhost:30080
- **Backend API**: http://localhost:30800

### **Network Access:**
```powershell
# Get your IP address
ipconfig | findstr IPv4

# Access from other devices on your network:
# Frontend: http://YOUR_IP:30080
# Backend: http://YOUR_IP:30800
```

### **NodePort Services:**
- Frontend exposed on port 30080
- Backend exposed on port 30800
- Accessible from any device on your local network

## 📊 Container Architecture

### **Running Containers (5 Application + 5 Infrastructure):**
- **2 Backend pods** (FastAPI replicas for load balancing)
- **2 Frontend pods** (React/Nginx replicas for high availability)
- **1 LDAP pod** (OpenLDAP server for authentication)
- **5 Kubernetes pause containers** (Pod infrastructure - normal behavior)

### **Auto-scaling:**
- Backend: 2-10 replicas based on CPU/memory usage
- Frontend: 2-5 replicas based on traffic
- LDAP: Single replica with persistent storage

## 🔐 Security Features

- **JWT-based authentication** with configurable expiration
- **Role-based access control** (admin, operator, personnel)
- **LDAP integration** for centralized user management
- **Network policies** for pod-to-pod communication security
- **Non-root containers** for enhanced security
- **Kubernetes Secrets** for encrypted sensitive data storage
- **Persistent encrypted storage** for LDAP data
- **Account lockout mechanism** (3 failed attempts → 30-second lockout)
- **Token refresh system** for extended sessions

## 💾 Data Persistence

### **User Data Storage:**
- **LDAP**: `C:\\ldap-data` and `C:\\ldap-config` (Windows host) mapped via Docker Desktop to `/run/desktop/mnt/host/c/...`
- **Database (TimescaleDB)**: PersistentVolumeClaim `timescaledb-data` within the cluster (no hostPath needed)
- **Persistence**: Survives container restarts, deployments, and system reboots
- **Backup**: Manual backup of these directories preserves all users

### **Required Directories:**
Before running the deployment, ensure these directories exist:
```powershell
# Create persistent storage directories
New-Item -ItemType Directory -Path "C:\ldap-data" -Force
New-Item -ItemType Directory -Path "C:\ldap-config" -Force
```

### **Adding Users:**
1. Add users through the web interface
2. Run `.\fresh-start.ps1` to test persistence
3. Users will be preserved across deployments

### **Data Recovery:**
- User data is stored in Windows directories
- Survives complete Docker/Kubernetes restarts
- Manual backup/restore possible via directory copy

## 🚨 Troubleshooting

### **LDAP Connection Issues**
```powershell
# Check LDAP pod status
kubectl get pods -n ldap-jwt-app -l app=ldap

# Check LDAP logs
kubectl logs deployment/ldap-deployment -n ldap-jwt-app

# Verify users exist
kubectl exec deployment/ldap-deployment -n ldap-jwt-app -- ldapsearch -x -H ldap://localhost -D "cn=admin,dc=example,dc=com" -w admin -b "ou=users,dc=example,dc=com" "(objectClass=inetOrgPerson)"
```

### **Pod Stuck in Pending**
```powershell
# Check persistent volumes
kubectl get pv,pvc -n ldap-jwt-app

# Fix persistent volume issues
kubectl delete pv ldap-data-pv-fixed ldap-config-pv-fixed --ignore-not-found=true
.\fresh-start.ps1
```

### **Network Access Issues**
```powershell
# Check NodePort services
kubectl get services -n ldap-jwt-app -o wide

# Verify your IP address
ipconfig | findstr IPv4

# Check Windows Firewall settings if needed
```

### **Container Issues**
```powershell
# Check all pod status
kubectl get pods -n ldap-jwt-app

# Check specific pod logs
kubectl logs <pod-name> -n ldap-jwt-app

# Restart deployment
kubectl rollout restart deployment/<deployment-name> -n ldap-jwt-app
```

### **Missing Directories Error**
If you encounter persistent volume binding issues:
```powershell
# Create required directories
New-Item -ItemType Directory -Path "C:\ldap-data" -Force
New-Item -ItemType Directory -Path "C:\ldap-config" -Force

# Redeploy
.\fresh-start.ps1
```

## 📁 Project Structure

```
├── k8s/                          # Kubernetes manifests
│   ├── namespace.yaml            # Application namespace
│   ├── persistent-volume.yaml    # Data persistence configuration
│   ├── configmap.yaml           # Application configuration
│   ├── secrets.yaml             # Encrypted sensitive data
│   ├── ldap-configmap.yaml      # LDAP bootstrap data
│   ├── ldap-deployment.yaml     # LDAP server deployment
│   ├── backend-deployment.yaml  # FastAPI backend deployment
│   ├── frontend-deployment.yaml # React frontend deployment
│   ├── frontend-nginx-config.yaml # Nginx configuration
│   ├── nodeport-services.yaml   # External access services
│   ├── network-policy.yaml      # Security policies
│   ├── hpa.yaml                 # Auto-scaling configuration
│   └── simple-nodeport.yaml     # Alternative service configuration
├── scripts/                     # Management scripts
│   ├── cleanup-keep-data.ps1    # Cleanup preserving data
│   ├── setup-ldap-users.ps1     # User setup script
│   ├── deploy.sh                # Linux deployment script
│   ├── cleanup.sh               # Linux cleanup script
│   └── build-images.sh          # Docker image build script
├── backend/                     # FastAPI backend source
├── frontend/                    # React frontend source
│   ├── src/                     # React source code
│   ├── public/                  # Static assets
│   ├── Dockerfile               # Frontend container image
│   ├── nginx.conf               # Nginx configuration
│   └── package.json             # Node.js dependencies
├── ldap/                        # LDAP bootstrap data
│   ├── 01-organizational-unit.ldif  # LDAP structure
│   └── 02-users.ldif           # Default user accounts
├── certs/                       # SSL certificates (if needed)
├── logs/                        # Application logs
├── main.py                      # FastAPI backend application
├── requirements.txt             # Python dependencies
├── Dockerfile.backend           # Backend container image
├── fresh-start.ps1              # Complete deployment script
├── shutdown.ps1                 # Complete shutdown script
├── PROJECT_REPORT.md            # Detailed project documentation
└── README.md                    # This comprehensive guide
```

## 🔄 Common Workflows

### **Daily Development:**
```powershell
# Start development
.\fresh-start.ps1

# Make changes to code
# (Edit files in backend/ or frontend/)

# Rebuild and redeploy
.\fresh-start.ps1
```

### **Add New Users:**
```powershell
# 1. Access frontend: http://localhost:30080
# 2. Login as admin (admin/admin123)
# 3. Add new users through interface
# 4. Test persistence:
.\fresh-start.ps1
# 5. Verify users still exist
```

### **Complete Reset (Keep Users):**
```powershell
# Clean deployment but keep user data
.\scripts\cleanup-keep-data.ps1

# Fresh deployment with preserved users
.\fresh-start.ps1
```

### **Complete Shutdown:**
```powershell
# Stop everything
.\shutdown.ps1

# Restart later
.\fresh-start.ps1
```

## 🚀 Production Considerations

### **For Production Deployment:**
1. **Container Registry**: Push images to ACR, ECR, or GCR
2. **Cloud Storage**: Use cloud persistent volumes instead of hostPath
3. **TLS/SSL**: Configure HTTPS with proper certificates
4. **Monitoring**: Add Prometheus/Grafana for metrics
5. **Logging**: Configure centralized logging (ELK stack)
6. **Backup Strategy**: Automated backup of LDAP data
7. **Secrets Management**: Use cloud secret management services
8. **Load Balancer**: Use cloud LoadBalancer instead of NodePort
9. **DNS**: Configure proper domain names
10. **High Availability**: Multi-node Kubernetes cluster

### **Scaling Configuration:**
- Backend automatically scales 2-10 replicas based on CPU (70% threshold)
- Frontend automatically scales 2-5 replicas based on traffic
- LDAP remains single replica with persistent storage
- Manual scaling: `kubectl scale deployment <name> --replicas=X -n ldap-jwt-app`

## 🔧 API Endpoints

### **Authentication Endpoints:**
- `POST /login` - User authentication
- `POST /refresh` - Refresh access token
- `POST /logout` - Logout current session
- `POST /logout-all` - Logout all devices
- `POST /verify-token` - Verify token validity

### **Admin Endpoints:**
- `GET /admin/users` - List all users
- `POST /admin/create-user` - Create new user
- `POST /admin/delete-user` - Delete user
- `POST /admin/reset-password` - Reset user password
- `POST /admin/change-role` - Change user role
- `POST /admin/change-authorization-level` - Change authorization level
- `POST /admin/unlock-account` - Unlock locked account
- `GET /admin/refresh-tokens` - List active refresh tokens

### **User Endpoints:**
- `GET /users/me` - Get current user info
- `GET /users/for-operator` - Get users for operator view
- `GET /users/operator-count` - Get user count for operators
- `GET /user/authorization-level/{username}` - Get user authorization level
- `GET /lockout-status/{username}` - Check account lockout status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test with `.\fresh-start.ps1`
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Quick Commands Reference

```powershell
# Deploy everything
.\fresh-start.ps1

# Shutdown everything  
.\shutdown.ps1

# Clean but keep data
.\scripts\cleanup-keep-data.ps1

# Check status
kubectl get pods -n ldap-jwt-app

# Get access URLs
ipconfig | findstr IPv4
# Frontend: http://YOUR_IP:30080
# Backend: http://YOUR_IP:30800

# Create required directories (if missing)
New-Item -ItemType Directory -Path "C:\ldap-data" -Force
New-Item -ItemType Directory -Path "C:\ldap-config" -Force
```

---

**🎊 Your LDAP JWT authentication system is ready to use with persistent data storage and easy management scripts!**

**⚠️ Important Note:** Before running the deployment, ensure the required directories `C:\ldap-data` and `C:\ldap-config` exist. These directories are automatically created by the deployment script, but if you encounter persistent volume binding issues, manually create them using the commands above. 