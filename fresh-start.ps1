# ============================================
# FRESH START WITH DATA PRESERVATION
# ============================================

Write-Host "Starting fresh deployment with data preservation..." -ForegroundColor Green

# 1. CLEANUP (preserves LDAP data)
Write-Host "Step 1: Cleaning up existing deployment..." -ForegroundColor Yellow
.\scripts\cleanup-keep-data.ps1

# 1.5. ADDITIONAL PV CLEANUP (fix binding issues)
Write-Host "Step 1.5: Fixing persistent volume bindings..." -ForegroundColor Yellow
# Remove any existing PVs that might be in Released state
kubectl delete pv ldap-data-pv-fixed ldap-config-pv-fixed --ignore-not-found=true
# Wait a moment for cleanup
Start-Sleep 5

# 2. BUILD DOCKER IMAGES
Write-Host "Step 2: Building Docker images..." -ForegroundColor Yellow
docker build -f Dockerfile.backend -t ldap-jwt-backend:latest .
docker build -f frontend/Dockerfile -t ldap-jwt-frontend:latest ./frontend

# 3. DEPLOY KUBERNETES RESOURCES
Write-Host "Step 3: Deploying Kubernetes resources..." -ForegroundColor Yellow

# Create namespace and core resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/persistent-volume.yaml

# Wait for PVs to be available
Write-Host "Waiting for persistent volumes to be available..." -ForegroundColor Cyan
Start-Sleep 3

kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/ldap-configmap.yaml
kubectl apply -f k8s/frontend-nginx-config.yaml

# Deploy LDAP server
Write-Host "Deploying LDAP server..." -ForegroundColor Cyan
kubectl apply -f k8s/ldap-deployment.yaml

# Wait for LDAP to be ready
Write-Host "Waiting for LDAP server to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=available --timeout=300s deployment/ldap-deployment -n ldap-jwt-app

# Deploy backend
Write-Host "Deploying backend..." -ForegroundColor Cyan
kubectl apply -f k8s/backend-deployment.yaml

# Wait for backend to be ready
Write-Host "Waiting for backend to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=available --timeout=300s deployment/backend-deployment -n ldap-jwt-app

# Deploy frontend
Write-Host "Deploying frontend..." -ForegroundColor Cyan
kubectl apply -f k8s/frontend-deployment.yaml

# Wait for frontend to be ready
Write-Host "Waiting for frontend to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=available --timeout=300s deployment/frontend-deployment -n ldap-jwt-app

# Deploy networking and scaling
Write-Host "Deploying networking and scaling..." -ForegroundColor Cyan
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/nodeport-services.yaml

# 4. VERIFY DEPLOYMENT
Write-Host "Step 4: Verifying deployment..." -ForegroundColor Yellow

Write-Host "Checking pod status..." -ForegroundColor Cyan
kubectl get pods -n ldap-jwt-app

Write-Host "Checking services..." -ForegroundColor Cyan
kubectl get services -n ldap-jwt-app

Write-Host "Checking persistent volumes..." -ForegroundColor Cyan
kubectl get pv,pvc -n ldap-jwt-app

# 5. GET ACCESS INFORMATION
Write-Host "Step 5: Access information..." -ForegroundColor Yellow

Write-Host "Getting your IP address..." -ForegroundColor Cyan
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.InterfaceAlias -notlike "*Teredo*"} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access your application:" -ForegroundColor White
Write-Host "Frontend: http://localhost:30080" -ForegroundColor Cyan
Write-Host "Frontend: http://$ipAddress:30080" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:30800" -ForegroundColor Cyan
Write-Host "Backend:  http://$ipAddress:30800" -ForegroundColor Cyan
Write-Host ""
Write-Host "Default Login Credentials:" -ForegroundColor White
Write-Host "admin / admin123 (admin role)" -ForegroundColor Green
Write-Host "operator1 / operator123 (operator role)" -ForegroundColor Green
Write-Host "user1 / user123 (personnel role)" -ForegroundColor Green
Write-Host ""
Write-Host "Data Storage:" -ForegroundColor White
Write-Host "LDAP Data: C:\ldap-data" -ForegroundColor Cyan
Write-Host "LDAP Config: C:\ldap-config" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your users will be preserved across deployments!" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green 