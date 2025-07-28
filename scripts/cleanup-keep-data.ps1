# Cleanup script that preserves LDAP data
# This will keep your users and configuration

Write-Host "Cleaning up deployment while preserving data..." -ForegroundColor Yellow

# Delete the namespace but keep persistent volumes
kubectl delete namespace ldap-jwt-app --ignore-not-found=true

# Wait for namespace deletion
Write-Host "Waiting for namespace cleanup..." -ForegroundColor Blue
do {
    Start-Sleep 2
    $namespaceExists = kubectl get namespace ldap-jwt-app 2>$null
} while ($namespaceExists)

# Clean up persistent volumes that are in Released state
Write-Host "Cleaning up released persistent volumes..." -ForegroundColor Blue
kubectl patch pv ldap-data-pv-fixed -p '{"spec":{"claimRef":null}}' 2>$null
kubectl patch pv ldap-config-pv-fixed -p '{"spec":{"claimRef":null}}' 2>$null

# Clean up old dynamic persistent volumes (but keep the manual ones)
Write-Host "Cleaning up old dynamic volumes..." -ForegroundColor Blue
kubectl get pv | Where-Object { $_ -match "pvc-.*hostpath.*Delete" } | ForEach-Object {
    $pvName = ($_ -split '\s+')[0]
    if ($pvName -and $pvName -ne "NAME") {
                    kubectl delete pv $pvName 2>$null
    }
}

# Stop Docker containers
Write-Host "Stopping Docker containers..." -ForegroundColor Blue
docker stop $(docker ps -q) 2>$null

# Clean up Docker system (but preserve images we built)
Write-Host "Cleaning up Docker system..." -ForegroundColor Blue
docker container prune -f

Write-Host "Cleanup completed! Your LDAP data is preserved." -ForegroundColor Green
Write-Host "Data location: C:\ldap-data" -ForegroundColor Cyan
Write-Host "Config location: C:\ldap-config" -ForegroundColor Cyan 