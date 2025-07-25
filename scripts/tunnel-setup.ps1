# WebSocket Tunnel Setup Script for LDAP-JWT Authentication Project (PowerShell)
# Supports multiple tunnel providers: CloudFlare, ngrok, localtunnel

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Provider = ""
)

$NAMESPACE = "ldap-jwt-app"
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

function Write-Info {
    param($Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Print-Banner {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║        WebSocket Tunnel Setup Manager        ║" -ForegroundColor Blue
    Write-Host "║     for LDAP-JWT Authentication Project      ║" -ForegroundColor Blue
    Write-Host "╚═══════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

function Show-Help {
    Write-Host "Usage: .\tunnel-setup.ps1 [COMMAND] [OPTIONS]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  deploy <provider>     Deploy tunnel (cloudflared|ngrok|localtunnel)"
    Write-Host "  remove <provider>     Remove tunnel deployment"
    Write-Host "  status               Show all tunnel statuses"
    Write-Host "  logs <provider>      Show tunnel logs"
    Write-Host "  urls                 Get tunnel URLs"
    Write-Host "  setup-tokens         Interactive token setup"
    Write-Host "  help                 Show this help"
    Write-Host ""
    Write-Host "Providers:"
    Write-Host "  cloudflared          Cloudflare Tunnel (requires token)"
    Write-Host "  ngrok               ngrok tunnel (requires auth token)"
    Write-Host "  localtunnel         localtunnel (no auth required)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\tunnel-setup.ps1 deploy localtunnel    # Quick deployment"
    Write-Host "  .\tunnel-setup.ps1 setup-tokens         # Setup tokens"
    Write-Host "  .\tunnel-setup.ps1 status               # Check status"
}

function Test-Prerequisites {
    # Check kubectl
    try {
        kubectl version --client | Out-Null
    }
    catch {
        Write-Error "kubectl is required but not found in PATH"
        exit 1
    }
    
    # Check namespace
    try {
        kubectl get namespace $NAMESPACE | Out-Null
    }
    catch {
        Write-Error "Namespace '$NAMESPACE' not found. Deploy your authentication project first."
        exit 1
    }
}

function Deploy-Tunnel {
    param($Provider)
    
    switch ($Provider) {
        "cloudflared" {
            Write-Info "Deploying Cloudflare Tunnel..."
            kubectl apply -f "$PROJECT_ROOT/k8s/tunnel-cloudflared.yaml"
            Write-Success "Cloudflare Tunnel deployed"
            Write-Warning "Remember to set up your tunnel token: .\tunnel-setup.ps1 setup-tokens"
        }
        "ngrok" {
            Write-Info "Deploying ngrok tunnel..."
            kubectl apply -f "$PROJECT_ROOT/k8s/tunnel-ngrok.yaml"
            Write-Success "ngrok tunnel deployed"
            Write-Warning "Remember to set up your auth token: .\tunnel-setup.ps1 setup-tokens"
        }
        "localtunnel" {
            Write-Info "Deploying localtunnel (no auth required)..."
            kubectl apply -f "$PROJECT_ROOT/k8s/tunnel-localtunnel.yaml"
            Write-Success "localtunnel deployed"
            Write-Info "Tunnel will be available in ~30 seconds"
        }
        default {
            Write-Error "Unknown provider: $Provider"
            Write-Host "Available providers: cloudflared, ngrok, localtunnel"
            exit 1
        }
    }
}

function Remove-Tunnel {
    param($Provider)
    
    switch ($Provider) {
        "cloudflared" {
            kubectl delete -f "$PROJECT_ROOT/k8s/tunnel-cloudflared.yaml" --ignore-not-found
            Write-Success "Cloudflare Tunnel removed"
        }
        "ngrok" {
            kubectl delete -f "$PROJECT_ROOT/k8s/tunnel-ngrok.yaml" --ignore-not-found
            Write-Success "ngrok tunnel removed"
        }
        "localtunnel" {
            kubectl delete -f "$PROJECT_ROOT/k8s/tunnel-localtunnel.yaml" --ignore-not-found
            Write-Success "localtunnel removed"
        }
        default {
            Write-Error "Unknown provider: $Provider"
            exit 1
        }
    }
}

function Show-Status {
    Write-Info "Tunnel Status Overview"
    Write-Host "======================"
    
    # Check CloudFlare
    try {
        $cfReady = kubectl get deployment cloudflared-tunnel -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>$null
        if ($cfReady -eq "1") {
            Write-Success "Cloudflare Tunnel: Running"
        } else {
            Write-Warning "Cloudflare Tunnel: Not Ready"
        }
    }
    catch {
        Write-Host "Cloudflare Tunnel: Not Deployed"
    }
    
    # Check ngrok
    try {
        $ngrokReady = kubectl get deployment ngrok-tunnel -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>$null
        if ($ngrokReady -eq "1") {
            Write-Success "ngrok Tunnel: Running"
        } else {
            Write-Warning "ngrok Tunnel: Not Ready"
        }
    }
    catch {
        Write-Host "ngrok Tunnel: Not Deployed"
    }
    
    # Check localtunnel
    try {
        $ltReady = kubectl get deployment localtunnel -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>$null
        if ($ltReady -eq "1") {
            Write-Success "localtunnel: Running"
        } else {
            Write-Warning "localtunnel: Not Ready"
        }
    }
    catch {
        Write-Host "localtunnel: Not Deployed"
    }
}

function Show-Logs {
    param($Provider)
    
    switch ($Provider) {
        "cloudflared" {
            kubectl logs -f deployment/cloudflared-tunnel -n $NAMESPACE --tail=50
        }
        "ngrok" {
            kubectl logs -f deployment/ngrok-tunnel -n $NAMESPACE --tail=50
        }
        "localtunnel" {
            kubectl logs -f deployment/localtunnel -n $NAMESPACE --tail=50
        }
        default {
            Write-Error "Unknown provider: $Provider"
            exit 1
        }
    }
}

function Get-URLs {
    Write-Info "Getting Tunnel URLs..."
    Write-Host "====================="
    
    # Local URLs
    Write-Host "Local URLs:" -ForegroundColor Blue
    Write-Host "  Frontend: http://localhost:30080"
    Write-Host "  Backend:  http://localhost:30800"
    Write-Host ""
    
    # localtunnel URLs
    try {
        kubectl get deployment localtunnel -n $NAMESPACE | Out-Null
        Write-Host "localtunnel URLs:" -ForegroundColor Green
        Write-Host "  Check logs: kubectl logs deployment/localtunnel -n $NAMESPACE"
        Write-Host "  Frontend: https://ldap-jwt-frontend.loca.lt"
        Write-Host "  Backend:  https://ldap-jwt-backend.loca.lt"
        Write-Host ""
    }
    catch {}
    
    # ngrok URLs
    try {
        kubectl get deployment ngrok-tunnel -n $NAMESPACE | Out-Null
        Write-Host "ngrok URLs:" -ForegroundColor Green
        Write-Host "  Web UI: http://localhost:30040"
        Write-Host "  API: Invoke-RestMethod http://localhost:30040/api/tunnels"
        Write-Host ""
    }
    catch {}
    
    Write-Info "For real-time URLs, check logs: .\tunnel-setup.ps1 logs <provider>"
}

function Setup-Tokens {
    Write-Info "Interactive Token Setup"
    Write-Host "======================"
    
    Write-Host "Choose tunnel provider to configure:"
    Write-Host "1) Cloudflare Tunnel"
    Write-Host "2) ngrok"
    Write-Host "3) Skip"
    
    $choice = Read-Host "Enter choice (1-3)"
    
    switch ($choice) {
        "1" { Setup-CloudflareToken }
        "2" { Setup-NgrokToken }
        "3" { Write-Info "Skipping token setup" }
        default { Write-Error "Invalid choice" }
    }
}

function Setup-CloudflareToken {
    Write-Info "Setting up Cloudflare Tunnel token..."
    Write-Host ""
    Write-Host "1. Go to https://dash.cloudflare.com/"
    Write-Host "2. Select your domain"
    Write-Host "3. Go to Zero Trust > Networks > Tunnels"
    Write-Host "4. Create a new tunnel or use existing"
    Write-Host "5. Copy the tunnel token"
    Write-Host ""
    
    $cfToken = Read-Host "Enter your Cloudflare tunnel token"
    
    if ($cfToken) {
        $encodedToken = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($cfToken))
        kubectl patch secret tunnel-secrets -n $NAMESPACE -p "{`"data`":{`"token`":`"$encodedToken`"}}"
        Write-Success "Cloudflare token configured"
    } else {
        Write-Warning "No token provided, skipping"
    }
}

function Setup-NgrokToken {
    Write-Info "Setting up ngrok auth token..."
    Write-Host ""
    Write-Host "1. Go to https://dashboard.ngrok.com/"
    Write-Host "2. Go to Your Authtoken"
    Write-Host "3. Copy your authtoken"
    Write-Host ""
    
    $ngrokToken = Read-Host "Enter your ngrok auth token"
    
    if ($ngrokToken) {
        $encodedToken = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($ngrokToken))
        kubectl patch secret ngrok-secrets -n $NAMESPACE -p "{`"data`":{`"authtoken`":`"$encodedToken`"}}"
        Write-Success "ngrok token configured"
    } else {
        Write-Warning "No token provided, skipping"
    }
}

# Main script execution
Print-Banner
Test-Prerequisites

switch ($Command.ToLower()) {
    "deploy" {
        if (-not $Provider) {
            Write-Error "Provider required. Usage: .\tunnel-setup.ps1 deploy <provider>"
            exit 1
        }
        Deploy-Tunnel $Provider
    }
    "remove" {
        if (-not $Provider) {
            Write-Error "Provider required. Usage: .\tunnel-setup.ps1 remove <provider>"
            exit 1
        }
        Remove-Tunnel $Provider
    }
    "status" {
        Show-Status
    }
    "logs" {
        if (-not $Provider) {
            Write-Error "Provider required. Usage: .\tunnel-setup.ps1 logs <provider>"
            exit 1
        }
        Show-Logs $Provider
    }
    "urls" {
        Get-URLs
    }
    "setup-tokens" {
        Setup-Tokens
    }
    "help" {
        Show-Help
    }
    default {
        Write-Error "Unknown command: $Command"
        Show-Help
        exit 1
    }
} 