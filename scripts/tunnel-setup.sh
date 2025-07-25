#!/bin/bash

# WebSocket Tunnel Setup Script for LDAP-JWT Authentication Project
# Supports multiple tunnel providers: CloudFlare, ngrok, localtunnel

set -e

NAMESPACE="ldap-jwt-app"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════╗"
    echo "║        WebSocket Tunnel Setup Manager        ║"
    echo "║     for LDAP-JWT Authentication Project      ║"
    echo "╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  deploy <provider>     Deploy tunnel (cloudflared|ngrok|localtunnel)"
    echo "  remove <provider>     Remove tunnel deployment"
    echo "  status               Show all tunnel statuses"
    echo "  logs <provider>      Show tunnel logs"
    echo "  urls                 Get tunnel URLs"
    echo "  setup-tokens         Interactive token setup"
    echo "  help                 Show this help"
    echo ""
    echo "Providers:"
    echo "  cloudflared          Cloudflare Tunnel (requires token)"
    echo "  ngrok               ngrok tunnel (requires auth token)"
    echo "  localtunnel         localtunnel (no auth required)"
    echo ""
    echo "Examples:"
    echo "  $0 deploy localtunnel    # Quick deployment without tokens"
    echo "  $0 setup-tokens         # Setup authentication tokens"
    echo "  $0 deploy cloudflared    # Deploy Cloudflare tunnel"
    echo "  $0 status               # Check all tunnel statuses"
    echo "  $0 urls                 # Get public URLs"
}

check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo_error "kubectl is required but not installed"
        exit 1
    fi
}

check_namespace() {
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        echo_error "Namespace '$NAMESPACE' not found. Please deploy your authentication project first."
        exit 1
    fi
}

deploy_tunnel() {
    local provider="$1"
    
    case "$provider" in
        cloudflared)
            echo_info "Deploying Cloudflare Tunnel..."
            kubectl apply -f "$PROJECT_ROOT/k8s/tunnel-cloudflared.yaml"
            echo_success "Cloudflare Tunnel deployed"
            echo_warning "Remember to set up your tunnel token: $0 setup-tokens"
            ;;
        ngrok)
            echo_info "Deploying ngrok tunnel..."
            kubectl apply -f "$PROJECT_ROOT/k8s/tunnel-ngrok.yaml"
            echo_success "ngrok tunnel deployed"
            echo_warning "Remember to set up your auth token: $0 setup-tokens"
            ;;
        localtunnel)
            echo_info "Deploying localtunnel (no auth required)..."
            kubectl apply -f "$PROJECT_ROOT/k8s/tunnel-localtunnel.yaml"
            echo_success "localtunnel deployed"
            echo_info "Tunnel will be available in ~30 seconds"
            ;;
        *)
            echo_error "Unknown provider: $provider"
            echo "Available providers: cloudflared, ngrok, localtunnel"
            exit 1
            ;;
    esac
}

remove_tunnel() {
    local provider="$1"
    
    case "$provider" in
        cloudflared)
            kubectl delete -f "$PROJECT_ROOT/k8s/tunnel-cloudflared.yaml" --ignore-not-found
            echo_success "Cloudflare Tunnel removed"
            ;;
        ngrok)
            kubectl delete -f "$PROJECT_ROOT/k8s/tunnel-ngrok.yaml" --ignore-not-found
            echo_success "ngrok tunnel removed"
            ;;
        localtunnel)
            kubectl delete -f "$PROJECT_ROOT/k8s/tunnel-localtunnel.yaml" --ignore-not-found
            echo_success "localtunnel removed"
            ;;
        *)
            echo_error "Unknown provider: $provider"
            exit 1
            ;;
    esac
}

show_status() {
    echo_info "Tunnel Status Overview"
    echo "======================"
    
    # Check CloudFlare
    if kubectl get deployment cloudflared-tunnel -n "$NAMESPACE" &> /dev/null; then
        local cf_ready=$(kubectl get deployment cloudflared-tunnel -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        if [ "$cf_ready" = "1" ]; then
            echo_success "Cloudflare Tunnel: Running"
        else
            echo_warning "Cloudflare Tunnel: Not Ready"
        fi
    else
        echo "Cloudflare Tunnel: Not Deployed"
    fi
    
    # Check ngrok
    if kubectl get deployment ngrok-tunnel -n "$NAMESPACE" &> /dev/null; then
        local ngrok_ready=$(kubectl get deployment ngrok-tunnel -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        if [ "$ngrok_ready" = "1" ]; then
            echo_success "ngrok Tunnel: Running"
        else
            echo_warning "ngrok Tunnel: Not Ready"
        fi
    else
        echo "ngrok Tunnel: Not Deployed"
    fi
    
    # Check localtunnel
    if kubectl get deployment localtunnel -n "$NAMESPACE" &> /dev/null; then
        local lt_ready=$(kubectl get deployment localtunnel -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        if [ "$lt_ready" = "1" ]; then
            echo_success "localtunnel: Running"
        else
            echo_warning "localtunnel: Not Ready"
        fi
    else
        echo "localtunnel: Not Deployed"
    fi
}

show_logs() {
    local provider="$1"
    
    case "$provider" in
        cloudflared)
            kubectl logs -f deployment/cloudflared-tunnel -n "$NAMESPACE" --tail=50
            ;;
        ngrok)
            kubectl logs -f deployment/ngrok-tunnel -n "$NAMESPACE" --tail=50
            ;;
        localtunnel)
            kubectl logs -f deployment/localtunnel -n "$NAMESPACE" --tail=50
            ;;
        *)
            echo_error "Unknown provider: $provider"
            exit 1
            ;;
    esac
}

get_urls() {
    echo_info "Getting Tunnel URLs..."
    echo "====================="
    
    # Local URLs (always available)
    echo -e "${BLUE}Local URLs:${NC}"
    echo "  Frontend: http://localhost:30080"
    echo "  Backend:  http://localhost:30800"
    echo ""
    
    # Try to get localtunnel URLs
    if kubectl get deployment localtunnel -n "$NAMESPACE" &> /dev/null; then
        echo -e "${GREEN}localtunnel URLs:${NC}"
        echo "  Check logs for URLs: kubectl logs deployment/localtunnel -n $NAMESPACE"
        echo "  Frontend: https://ldap-jwt-frontend.loca.lt"
        echo "  Backend:  https://ldap-jwt-backend.loca.lt"
        echo ""
    fi
    
    # Try to get ngrok URLs
    if kubectl get deployment ngrok-tunnel -n "$NAMESPACE" &> /dev/null; then
        echo -e "${GREEN}ngrok URLs:${NC}"
        echo "  Web UI: http://localhost:30040"
        echo "  API: curl http://localhost:30040/api/tunnels"
        echo ""
    fi
    
    echo_info "For real-time URLs, check the logs: $0 logs <provider>"
}

setup_tokens() {
    echo_info "Interactive Token Setup"
    echo "======================"
    
    echo "Choose tunnel provider to configure:"
    echo "1) Cloudflare Tunnel"
    echo "2) ngrok"
    echo "3) Skip"
    read -p "Enter choice (1-3): " choice
    
    case "$choice" in
        1)
            setup_cloudflare_token
            ;;
        2)
            setup_ngrok_token
            ;;
        3)
            echo_info "Skipping token setup"
            ;;
        *)
            echo_error "Invalid choice"
            ;;
    esac
}

setup_cloudflare_token() {
    echo_info "Setting up Cloudflare Tunnel token..."
    echo ""
    echo "1. Go to https://dash.cloudflare.com/"
    echo "2. Select your domain"
    echo "3. Go to Zero Trust > Networks > Tunnels"
    echo "4. Create a new tunnel or use existing"
    echo "5. Copy the tunnel token"
    echo ""
    read -p "Enter your Cloudflare tunnel token: " cf_token
    
    if [ -n "$cf_token" ]; then
        # Encode token in base64
        echo -n "$cf_token" | base64 > /tmp/cf_token_b64
        kubectl patch secret tunnel-secrets -n "$NAMESPACE" -p "{\"data\":{\"token\":\"$(cat /tmp/cf_token_b64)\"}}"
        rm /tmp/cf_token_b64
        echo_success "Cloudflare token configured"
    else
        echo_warning "No token provided, skipping"
    fi
}

setup_ngrok_token() {
    echo_info "Setting up ngrok auth token..."
    echo ""
    echo "1. Go to https://dashboard.ngrok.com/"
    echo "2. Go to Your Authtoken"
    echo "3. Copy your authtoken"
    echo ""
    read -p "Enter your ngrok auth token: " ngrok_token
    
    if [ -n "$ngrok_token" ]; then
        # Encode token in base64
        echo -n "$ngrok_token" | base64 > /tmp/ngrok_token_b64
        kubectl patch secret ngrok-secrets -n "$NAMESPACE" -p "{\"data\":{\"authtoken\":\"$(cat /tmp/ngrok_token_b64)\"}}"
        rm /tmp/ngrok_token_b64
        echo_success "ngrok token configured"
    else
        echo_warning "No token provided, skipping"
    fi
}

# Main script logic
print_banner

check_kubectl
check_namespace

case "${1:-help}" in
    deploy)
        if [ -z "$2" ]; then
            echo_error "Provider required. Usage: $0 deploy <provider>"
            exit 1
        fi
        deploy_tunnel "$2"
        ;;
    remove)
        if [ -z "$2" ]; then
            echo_error "Provider required. Usage: $0 remove <provider>"
            exit 1
        fi
        remove_tunnel "$2"
        ;;
    status)
        show_status
        ;;
    logs)
        if [ -z "$2" ]; then
            echo_error "Provider required. Usage: $0 logs <provider>"
            exit 1
        fi
        show_logs "$2"
        ;;
    urls)
        get_urls
        ;;
    setup-tokens)
        setup_tokens
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 