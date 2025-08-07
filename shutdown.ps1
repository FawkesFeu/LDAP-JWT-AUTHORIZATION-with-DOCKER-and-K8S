# ============================================
# COMPLETE SHUTDOWN SCRIPT
# ============================================

Write-Host "Starting complete shutdown of LDAP-JWT application..." -ForegroundColor Red

# 1. DELETE KUBERNETES DEPLOYMENT
Write-Host "Step 1: Deleting Kubernetes deployment..." -ForegroundColor Yellow
kubectl delete namespace ldap-jwt-app --ignore-not-found=true

# Wait for namespace deletion
Write-Host "Waiting for namespace deletion..." -ForegroundColor Cyan
do {
    Start-Sleep 2
    $namespaceExists = kubectl get namespace ldap-jwt-app 2>$null
} while ($namespaceExists)

# 2. CLEAN UP PERSISTENT VOLUMES
Write-Host "Step 2: Cleaning up persistent volumes..." -ForegroundColor Yellow

# Clean up database PVCs first (to release PVs)
kubectl delete pvc -n ldap-jwt-app --ignore-not-found=true

# Wait for PVCs to be deleted
Write-Host "Waiting for PVCs to be deleted..." -ForegroundColor Cyan
Start-Sleep 10

# Clean up any remaining dynamic volumes
kubectl get pv | Where-Object { $_ -match "pvc-.*" } | ForEach-Object {
    $pvName = ($_ -split '\s+')[0]
    if ($pvName -and $pvName -ne "NAME") {
        kubectl delete pv $pvName --ignore-not-found=true
    }
}

# Note: We preserve LDAP data volumes (ldap-data-pv-fixed, ldap-config-pv-fixed)
# These will be reused on next startup

# 3. STOP ALL DOCKER CONTAINERS
Write-Host "Step 3: Stopping all Docker containers..." -ForegroundColor Yellow
$containers = docker ps -q
if ($containers) {
    docker stop $containers
    Write-Host "All containers stopped." -ForegroundColor Green
} else {
    Write-Host "No containers running." -ForegroundColor Green
}

# 4. REMOVE ALL CONTAINERS
Write-Host "Step 4: Removing all containers..." -ForegroundColor Yellow
docker container prune -f

# 5. CLEAN UP DOCKER SYSTEM (OPTIONAL)
Write-Host "Step 5: Docker system cleanup..." -ForegroundColor Yellow
$cleanup = Read-Host "Do you want to clean up Docker images and volumes? (y/N)"
if ($cleanup -eq "y" -or $cleanup -eq "Y") {
    Write-Host "Cleaning up Docker images and volumes..." -ForegroundColor Cyan
    docker system prune -af --volumes
    Write-Host "Docker system cleaned." -ForegroundColor Green
} else {
    Write-Host "Skipping Docker system cleanup." -ForegroundColor Cyan
}

# 6. VERIFICATION
Write-Host "Step 6: Verification..." -ForegroundColor Yellow

Write-Host "Checking Kubernetes resources..." -ForegroundColor Cyan
$k8sResources = kubectl get all --all-namespaces | findstr ldap-jwt
if (-not $k8sResources) {
    Write-Host "No Kubernetes resources found." -ForegroundColor Green
} else {
    Write-Host "Some Kubernetes resources may still exist." -ForegroundColor Yellow
}

Write-Host "Checking Docker containers..." -ForegroundColor Cyan
$runningContainers = docker ps --format "table {{.Names}}\t{{.Status}}"
if ($runningContainers -eq "NAMES`tSTATUS") {
    Write-Host "No containers running." -ForegroundColor Green
} else {
    Write-Host "Running containers:" -ForegroundColor Cyan
    docker ps --format "table {{.Names}}\t{{.Status}}"
}

# Final Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "SHUTDOWN COMPLETED!" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

Write-Host "What was cleaned up:" -ForegroundColor White
Write-Host "Kubernetes namespace and all resources" -ForegroundColor Green
Write-Host "Persistent volumes" -ForegroundColor Green
Write-Host "All Docker containers" -ForegroundColor Green
if ($cleanup -eq "y" -or $cleanup -eq "Y") {
    Write-Host "Docker images and volumes" -ForegroundColor Green
}

Write-Host ""
Write-Host "Data preservation:" -ForegroundColor White
Write-Host "LDAP data preserved at: C:\ldap-data" -ForegroundColor Cyan
Write-Host "LDAP config preserved at: C:\ldap-config" -ForegroundColor Cyan
Write-Host "Database data preserved (TimescaleDB PVC)" -ForegroundColor Cyan
Write-Host "User accounts and settings preserved" -ForegroundColor Cyan
Write-Host ""

Write-Host "To restart: Run .\fresh-start.ps1" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Red
