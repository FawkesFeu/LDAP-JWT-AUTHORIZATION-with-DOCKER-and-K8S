# PowerShell script to check migration status and verify persistent IDs

Write-Host "🔍 Checking Migration Status" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# Check if migration job exists and its status
Write-Host "`nStep 1: Checking migration job status..." -ForegroundColor Yellow
try {
    $jobStatus = kubectl get job user-migration-job -n ldap-jwt-app --no-headers 2>$null
    if ($jobStatus) {
        Write-Host "✅ Migration job found" -ForegroundColor Green
        kubectl get job user-migration-job -n ldap-jwt-app
    } else {
        Write-Host "⚠️ Migration job not found - run fresh-start.ps1 first" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error checking job status: $_" -ForegroundColor Red
}

# Check migration logs
Write-Host "`nStep 2: Checking migration logs..." -ForegroundColor Yellow
try {
    $logs = kubectl logs job/user-migration-job -n ldap-jwt-app 2>$null
    if ($logs) {
        Write-Host "Migration logs:" -ForegroundColor Cyan
        Write-Host $logs -ForegroundColor White
    } else {
        Write-Host "⚠️ No migration logs found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error getting logs: $_" -ForegroundColor Red
}

# Check if table population job exists and its status
Write-Host "`nStep 3: Checking table population job status..." -ForegroundColor Yellow
try {
    $jobStatus = kubectl get job populate-tables-job -n ldap-jwt-app --no-headers 2>$null
    if ($jobStatus) {
        Write-Host "✅ Table population job found" -ForegroundColor Green
        kubectl get job populate-tables-job -n ldap-jwt-app
    } else {
        Write-Host "⚠️ Table population job not found - run fresh-start.ps1 first" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error checking job status: $_" -ForegroundColor Red
}

# Check table population logs
Write-Host "`nStep 4: Checking table population logs..." -ForegroundColor Yellow
try {
    $logs = kubectl logs job/populate-tables-job -n ldap-jwt-app 2>$null
    if ($logs) {
        Write-Host "Table population logs:" -ForegroundColor Cyan
        Write-Host $logs -ForegroundColor White
    } else {
        Write-Host "⚠️ No table population logs found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error getting logs: $_" -ForegroundColor Red
}

# Check database schema
Write-Host "`nStep 5: Checking database schema..." -ForegroundColor Yellow
try {
    $dbPod = kubectl get pods -n ldap-jwt-app -l app=timescaledb --no-headers | Select-Object -First 1
    if ($dbPod) {
        Write-Host "✅ Database pod found" -ForegroundColor Green
        
        # Check if new tables exist
        $tables = kubectl exec -n ldap-jwt-app deployment/timescaledb-deployment -- psql -U postgres -d auth_metadata -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('operators', 'personnel');" 2>$null
        
        if ($tables -match 'operators|personnel') {
            Write-Host "✅ New tables (operators, personnel) exist" -ForegroundColor Green
        } else {
            Write-Host "⚠️ New tables not found - schema may not be applied" -ForegroundColor Yellow
        }
        
        # Check sequences
        $sequences = kubectl exec -n ldap-jwt-app deployment/timescaledb-deployment -- psql -U postgres -d auth_metadata -c "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public' AND sequence_name LIKE '%_id_seq';" 2>$null
        
        if ($sequences -match 'admin_id_seq|operator_id_seq|personnel_id_seq') {
            Write-Host "✅ ID sequences exist" -ForegroundColor Green
        } else {
            Write-Host "⚠️ ID sequences not found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Database pod not found" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error checking database: $_" -ForegroundColor Red
}

Write-Host "`n🎉 Migration status check completed!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. If migration failed, run fresh-start.ps1 again" -ForegroundColor White
Write-Host "2. Test creating new users to verify persistent IDs work" -ForegroundColor White
Write-Host "3. Check that user IDs remain consistent across restarts" -ForegroundColor White 