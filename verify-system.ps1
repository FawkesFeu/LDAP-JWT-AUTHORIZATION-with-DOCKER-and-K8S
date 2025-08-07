# ============================================
# SYSTEM VERIFICATION SCRIPT
# ============================================

Write-Host "Verifying LDAP-JWT system status..." -ForegroundColor Green

# 1. CHECK KUBERNETES PODS
Write-Host "Step 1: Checking Kubernetes pods..." -ForegroundColor Yellow
$pods = kubectl get pods -n ldap-jwt-app --no-headers
$allRunning = $true

foreach ($pod in $pods) {
    $podInfo = $pod -split '\s+'
    $podName = $podInfo[0]
    $podStatus = $podInfo[2]
    
    if ($podStatus -eq "Running") {
        Write-Host "✅ $podName is running" -ForegroundColor Green
    } else {
        Write-Host "❌ $podName status: $podStatus" -ForegroundColor Red
        $allRunning = $false
    }
}

# 2. CHECK SERVICES
Write-Host "`nStep 2: Checking services..." -ForegroundColor Yellow
$services = kubectl get services -n ldap-jwt-app --no-headers
foreach ($service in $services) {
    $serviceInfo = $service -split '\s+'
    $serviceName = $serviceInfo[0]
    Write-Host "✅ Service $serviceName is available" -ForegroundColor Green
}

# 3. CHECK PERSISTENT VOLUMES
Write-Host "`nStep 3: Checking persistent volumes..." -ForegroundColor Yellow
$pvs = kubectl get pv --no-headers | Where-Object { $_ -match "ldap-jwt" }
foreach ($pv in $pvs) {
    $pvInfo = $pv -split '\s+'
    $pvName = $pvInfo[0]
    $pvStatus = $pvInfo[4]
    Write-Host "✅ PV $pvName status: $pvStatus" -ForegroundColor Green
}

# 4. CHECK DATABASE CONNECTION
Write-Host "`nStep 4: Checking database connection..." -ForegroundColor Yellow
try {
    $dbPod = kubectl get pods -n ldap-jwt-app -l app=timescaledb --no-headers | Select-Object -First 1
    if ($dbPod -and $dbPod -match "Running") {
        Write-Host "✅ TimescaleDB is running" -ForegroundColor Green
        
        # Check if schema is applied
        $schemaCheck = kubectl exec deployment/backend-deployment -n ldap-jwt-app -- python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='timescaledb-service',
        port='5432',
        database='auth_metadata',
        user='postgres',
        password='auth_metadata_pass'
    )
    with conn.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        print(f'Users in database: {count}')
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database error: {e}')
" 2>$null
        
        if ($schemaCheck -match "Database connection successful") {
            Write-Host "✅ Database schema is applied" -ForegroundColor Green
            if ($schemaCheck -match "Users in database:") {
                Write-Host "✅ Database has user data" -ForegroundColor Green
            }
        } else {
            Write-Host "⚠️ Database schema may not be fully applied" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ TimescaleDB is not running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not check database: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. CHECK LDAP CONNECTION
Write-Host "`nStep 5: Checking LDAP connection..." -ForegroundColor Yellow
try {
    $ldapPod = kubectl get pods -n ldap-jwt-app -l app=ldap --no-headers | Select-Object -First 1
    if ($ldapPod -and $ldapPod -match "Running") {
        Write-Host "✅ LDAP server is running" -ForegroundColor Green
        
        # Check if users exist in LDAP
        $ldapUsers = kubectl exec deployment/ldap-deployment -n ldap-jwt-app -- ldapsearch -x -H ldap://localhost -D "cn=admin,dc=example,dc=com" -w admin -b "ou=users,dc=example,dc=com" "(objectClass=inetOrgPerson)" uid 2>$null
        
        if ($ldapUsers -match "uid:") {
            Write-Host "✅ LDAP has user data" -ForegroundColor Green
        } else {
            Write-Host "⚠️ LDAP may not have user data" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ LDAP server is not running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not check LDAP: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. CHECK BACKEND API
Write-Host "`nStep 6: Checking backend API..." -ForegroundColor Yellow
try {
    $backendPod = kubectl get pods -n ldap-jwt-app -l app=backend --no-headers | Select-Object -First 1
    if ($backendPod -and $backendPod -match "Running") {
        Write-Host "✅ Backend is running" -ForegroundColor Green
        
        # Check if API is responding
        $apiResponse = kubectl exec deployment/backend-deployment -n ldap-jwt-app -- curl -s http://localhost:8000/docs 2>$null
        if ($apiResponse -match "FastAPI") {
            Write-Host "✅ Backend API is responding" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Backend API may not be fully ready" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Backend is not running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not check backend: $($_.Exception.Message)" -ForegroundColor Red
}

# 7. CHECK FRONTEND
Write-Host "`nStep 7: Checking frontend..." -ForegroundColor Yellow
try {
    $frontendPod = kubectl get pods -n ldap-jwt-app -l app=frontend --no-headers | Select-Object -First 1
    if ($frontendPod -and $frontendPod -match "Running") {
        Write-Host "✅ Frontend is running" -ForegroundColor Green
    } else {
        Write-Host "❌ Frontend is not running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not check frontend: $($_.Exception.Message)" -ForegroundColor Red
}

# 8. CHECK MIGRATION JOBS
Write-Host "`nStep 8: Checking migration jobs..." -ForegroundColor Yellow
$migrationJob = kubectl get jobs -n ldap-jwt-app user-migration-job --no-headers 2>$null
$populationJob = kubectl get jobs -n ldap-jwt-app populate-tables-job --no-headers 2>$null

if ($migrationJob -and $migrationJob -match "1/1") {
    Write-Host "✅ Migration job completed successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️ Migration job may not have completed" -ForegroundColor Yellow
}

if ($populationJob -and $populationJob -match "1/1") {
    Write-Host "✅ Population job completed successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️ Population job may not have completed" -ForegroundColor Yellow
}

# 9. FINAL SUMMARY
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "SYSTEM VERIFICATION COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

if ($allRunning) {
    Write-Host "`n🎉 All systems are running!" -ForegroundColor Green
    Write-Host "`nAccess your application:" -ForegroundColor White
    Write-Host "Frontend: http://localhost:30080" -ForegroundColor Cyan
    Write-Host "Backend:  http://localhost:30800" -ForegroundColor Cyan
    Write-Host "Database: localhost:30432" -ForegroundColor Cyan
    Write-Host "`nDefault users:" -ForegroundColor White
    Write-Host "admin / admin123 (admin role)" -ForegroundColor Green
    Write-Host "operator1 / operator123 (operator role)" -ForegroundColor Green
    Write-Host "user1 / user123 (personnel role)" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Some components may not be running properly" -ForegroundColor Yellow
    Write-Host "Check the logs above for details" -ForegroundColor Yellow
}

Write-Host "`nTo check detailed logs:" -ForegroundColor White
Write-Host "kubectl logs deployment/backend-deployment -n ldap-jwt-app" -ForegroundColor Cyan
Write-Host "kubectl logs deployment/ldap-deployment -n ldap-jwt-app" -ForegroundColor Cyan
Write-Host "kubectl logs job/user-migration-job -n ldap-jwt-app" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
