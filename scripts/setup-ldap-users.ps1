# LDAP User Setup Script
# This script checks if users exist and adds them if they don't

Write-Host "Checking LDAP user setup..." -ForegroundColor Yellow

# Check if LDAP pod is running
$ldapPod = kubectl get pods -n ldap-jwt-app -l app=ldap --no-headers
if (-not $ldapPod -or $ldapPod -notmatch "1/1\s+Running") {
    Write-Host "❌ LDAP pod is not running. Please ensure it's deployed first." -ForegroundColor Red
    exit 1
}

# Function to check if entry exists
function Test-LdapEntry {
    param($dn)
    $result = kubectl exec deployment/ldap-deployment -n ldap-jwt-app -- ldapsearch -x -H ldap://localhost -D "cn=admin,dc=example,dc=com" -w admin -b "$dn" "(objectClass=*)" 2>$null
    return $result -match "numEntries: 1"
}

# Function to add LDAP entry
function Add-LdapEntry {
    param($ldifContent, $description)
    Write-Host "Adding $description..." -ForegroundColor Green
    $ldifContent | kubectl exec -i deployment/ldap-deployment -n ldap-jwt-app -- ldapadd -x -H ldap://localhost -D "cn=admin,dc=example,dc=com" -w admin
}

# Check and create users OU
if (-not (Test-LdapEntry "ou=users,dc=example,dc=com")) {
    Write-Host "Creating users organizational unit..."
    $usersOU = @"
dn: ou=users,dc=example,dc=com
objectClass: top
objectClass: organizationalUnit
ou: users
"@
    Add-LdapEntry $usersOU "users organizational unit"
} else {
    Write-Host "✅ Users OU already exists" -ForegroundColor Green
}

# Check and create admin user
if (-not (Test-LdapEntry "uid=admin,ou=users,dc=example,dc=com")) {
    $adminUser = @"
dn: uid=admin,ou=users,dc=example,dc=com
objectClass: top
objectClass: inetOrgPerson
uid: admin
cn: Administrator
sn: Administrator
userPassword: admin123
employeeType: admin
employeeNumber: ADMIN_01
"@
    Add-LdapEntry $adminUser "admin user"
} else {
    Write-Host "✅ Admin user already exists" -ForegroundColor Green
}

# Check and create operator user
if (-not (Test-LdapEntry "uid=operator1,ou=users,dc=example,dc=com")) {
    $operatorUser = @"
dn: uid=operator1,ou=users,dc=example,dc=com
objectClass: top
objectClass: inetOrgPerson
uid: operator1
cn: Operator One
sn: One
userPassword: operator123
employeeType: operator
employeeNumber: OP_01
"@
    Add-LdapEntry $operatorUser "operator user"
} else {
    Write-Host "✅ Operator user already exists" -ForegroundColor Green
}

# Check and create personnel user
if (-not (Test-LdapEntry "uid=user1,ou=users,dc=example,dc=com")) {
    $personnelUser = @"
dn: uid=user1,ou=users,dc=example,dc=com
objectClass: top
objectClass: inetOrgPerson
uid: user1
cn: User One
sn: One
userPassword: user123
employeeType: personnel
employeeNumber: PER_01
"@
    Add-LdapEntry $personnelUser "personnel user"
} else {
    Write-Host "✅ Personnel user already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 LDAP user setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Available users:" -ForegroundColor Cyan
Write-Host "  admin     / admin123    (admin role)" -ForegroundColor White
Write-Host "  operator1 / operator123 (operator role)" -ForegroundColor White
Write-Host "  user1     / user123     (personnel role)" -ForegroundColor White
Write-Host ""
Write-Host "Access your application at: http://localhost:30080" -ForegroundColor Yellow 