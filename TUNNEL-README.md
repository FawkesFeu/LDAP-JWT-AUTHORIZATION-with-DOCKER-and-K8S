# 🌐 WebSocket Tunnel Setup for LDAP-JWT Authentication Project

**Share your authentication app with friends and colleagues via secure tunnels with full WebSocket support!**

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [🚀 Quick Start](#-quick-start)
- [🔧 Tunnel Providers](#-tunnel-providers)
- [📦 Installation](#-installation)
- [💡 Usage Examples](#-usage-examples)
- [🔐 Security & Authentication](#-security--authentication)
- [🔍 Troubleshooting](#-troubleshooting)
- [🧹 Cleanup](#-cleanup)

## 🎯 Overview

This tunneling solution enables you to:

✅ **Share your LDAP-JWT authentication app** with anyone, anywhere  
✅ **Full WebSocket support** for real-time features  
✅ **Multiple tunnel providers** (Cloudflare, ngrok, localtunnel)  
✅ **Kubernetes-native** deployment and management  
✅ **Auto-restart** on pod rescheduling  
✅ **Easy setup** with management scripts  
✅ **Cross-platform** (Windows PowerShell + Linux/macOS Bash)

## 🚀 Quick Start

**For immediate sharing (no signup required):**

### Windows (PowerShell)
```powershell
# Deploy localtunnel (no auth needed)
.\scripts\tunnel-setup.ps1 deploy localtunnel

# Check status
.\scripts\tunnel-setup.ps1 status

# Get shareable URLs
.\scripts\tunnel-setup.ps1 urls

# View logs for actual URLs
.\scripts\tunnel-setup.ps1 logs localtunnel
```

### Linux/macOS (Bash)
```bash
# Make script executable
chmod +x scripts/tunnel-setup.sh

# Deploy localtunnel (no auth needed)
./scripts/tunnel-setup.sh deploy localtunnel

# Check status
./scripts/tunnel-setup.sh status

# Get shareable URLs
./scripts/tunnel-setup.sh urls

# View logs for actual URLs
./scripts/tunnel-setup.sh logs localtunnel
```

**Your app will be available at URLs like:**
- **Frontend:** `https://ldap-jwt-frontend.loca.lt`
- **Backend API:** `https://ldap-jwt-backend.loca.lt`

## 🔧 Tunnel Providers

### 1. 🟦 **localtunnel** (Recommended for Quick Testing)
- ✅ **No signup required**
- ✅ **Instant deployment**  
- ✅ **WebSocket support**
- ⚠️ **URLs change on restart**
- ⚠️ **Rate limiting**

**Best for:** Development, quick demos, internal sharing

### 2. 🟧 **Cloudflare Tunnel** (Recommended for Production)
- ✅ **Professional service**
- ✅ **Stable URLs**
- ✅ **Excellent WebSocket support**
- ✅ **DDoS protection**
- 🔑 **Requires Cloudflare account**

**Best for:** Production sharing, stable demos, external access

### 3. 🟪 **ngrok** (Popular Choice)
- ✅ **Well-known service**
- ✅ **Great documentation**
- ✅ **Web inspection UI**
- 🔑 **Requires ngrok account**
- 💰 **Free tier limitations**

**Best for:** Development, debugging, temporary sharing

## 📦 Installation

### Prerequisites

1. **Kubernetes cluster running** (Docker Desktop, minikube, etc.)
2. **Your LDAP-JWT app deployed** in the `ldap-jwt-app` namespace
3. **kubectl configured** and accessible

### Deploy Tunnel Files

1. **Ensure your authentication project is running:**
   ```bash
   kubectl get pods -n ldap-jwt-app
   ```

2. **Deploy tunnel configuration:**
   ```bash
   # Choose your preferred method:
   
   # Option 1: localtunnel (no auth)
   kubectl apply -f k8s/tunnel-localtunnel.yaml
   
   # Option 2: Cloudflare (requires token)
   kubectl apply -f k8s/tunnel-cloudflared.yaml
   
   # Option 3: ngrok (requires token)
   kubectl apply -f k8s/tunnel-ngrok.yaml
   ```

3. **Configure authentication tokens** (if using Cloudflare/ngrok):
   ```bash
   # Interactive setup
   ./scripts/tunnel-setup.sh setup-tokens
   ```

## 💡 Usage Examples

### Example 1: Quick Demo Setup

```bash
# Deploy localtunnel for instant sharing
./scripts/tunnel-setup.sh deploy localtunnel

# Wait 30 seconds, then check logs for URLs
./scripts/tunnel-setup.sh logs localtunnel

# Share the URLs with your team!
```

### Example 2: Production-Ready Sharing

```bash
# 1. Set up Cloudflare tunnel token
./scripts/tunnel-setup.sh setup-tokens

# 2. Deploy Cloudflare tunnel
./scripts/tunnel-setup.sh deploy cloudflared

# 3. Monitor status
./scripts/tunnel-setup.sh status

# 4. Get stable URLs
./scripts/tunnel-setup.sh logs cloudflared
```

### Example 3: Development with ngrok

```bash
# 1. Configure ngrok auth token
./scripts/tunnel-setup.sh setup-tokens

# 2. Deploy ngrok tunnel
./scripts/tunnel-setup.sh deploy ngrok

# 3. Access ngrok web UI at http://localhost:30040
# 4. Monitor traffic and debug issues
```

## 🔐 Security & Authentication

### Cloudflare Tunnel Setup

1. **Create Cloudflare account** at https://dash.cloudflare.com/
2. **Add your domain** (or use Cloudflare's subdomain)
3. **Navigate to:** Zero Trust > Networks > Tunnels
4. **Create tunnel** and copy the token
5. **Configure token:**
   ```bash
   ./scripts/tunnel-setup.sh setup-tokens
   # Choose option 1 (Cloudflare)
   # Paste your tunnel token
   ```

### ngrok Setup

1. **Create ngrok account** at https://dashboard.ngrok.com/
2. **Get your authtoken** from the dashboard
3. **Configure token:**
   ```bash
   ./scripts/tunnel-setup.sh setup-tokens
   # Choose option 2 (ngrok)
   # Paste your auth token
   ```

### Manual Token Configuration

If you prefer manual configuration:

```bash
# Cloudflare token
kubectl patch secret tunnel-secrets -n ldap-jwt-app \
  -p '{"data":{"token":"'$(echo -n "YOUR_TOKEN" | base64)'"}}'

# ngrok token  
kubectl patch secret ngrok-secrets -n ldap-jwt-app \
  -p '{"data":{"authtoken":"'$(echo -n "YOUR_TOKEN" | base64)'"}}'
```

## 🔍 Troubleshooting

### Common Issues

#### ❌ "Namespace not found"
```bash
# Verify your authentication project is deployed
kubectl get namespaces | grep ldap-jwt-app

# If missing, deploy your main project first
kubectl apply -f k8s/namespace.yaml
# ... deploy other components
```

#### ❌ "localtunnel URLs not working"
```bash
# Check pod logs for actual URLs
kubectl logs deployment/localtunnel -n ldap-jwt-app

# Look for lines like:
# "your url is: https://abc123.loca.lt"
```

#### ❌ "Cloudflare tunnel not connecting"
```bash
# Check if token is configured
kubectl get secret tunnel-secrets -n ldap-jwt-app -o yaml

# Check tunnel logs
kubectl logs deployment/cloudflared-tunnel -n ldap-jwt-app

# Common fixes:
# 1. Verify token is correct
# 2. Check Cloudflare dashboard for tunnel status
# 3. Ensure domain DNS is configured
```

#### ❌ "ngrok authentication failed"
```bash
# Verify auth token
kubectl get secret ngrok-secrets -n ldap-jwt-app -o yaml

# Check ngrok logs
kubectl logs deployment/ngrok-tunnel -n ldap-jwt-app

# Common fixes:
# 1. Verify authtoken from ngrok dashboard
# 2. Check account limits (free tier restrictions)
```

### Debug Commands

```bash
# Check all tunnel statuses
./scripts/tunnel-setup.sh status

# View real-time logs
./scripts/tunnel-setup.sh logs <provider>

# Check pod status
kubectl get pods -n ldap-jwt-app | grep tunnel

# Describe pod for detailed info
kubectl describe pod <tunnel-pod-name> -n ldap-jwt-app

# Check services
kubectl get svc -n ldap-jwt-app
```

### Performance Issues

#### WebSocket Connection Problems
```bash
# Check if WebSocket upgrade headers are present
kubectl logs deployment/cloudflared-tunnel -n ldap-jwt-app | grep -i websocket

# For ngrok, check web UI at http://localhost:30040
```

#### High Latency
```bash
# Test direct connection vs tunnel
curl -w "@{total_time: %{time_total}s}\n" http://localhost:30080
curl -w "@{total_time: %{time_total}s}\n" https://your-tunnel-url.com

# Consider using Cloudflare for better performance
```

## 🧹 Cleanup

### Remove Specific Tunnel

```bash
# Remove localtunnel
./scripts/tunnel-setup.sh remove localtunnel

# Remove Cloudflare tunnel
./scripts/tunnel-setup.sh remove cloudflared

# Remove ngrok tunnel
./scripts/tunnel-setup.sh remove ngrok
```

### Remove All Tunnels

```bash
# Remove all tunnel deployments
kubectl delete -f k8s/tunnel-localtunnel.yaml --ignore-not-found
kubectl delete -f k8s/tunnel-cloudflared.yaml --ignore-not-found
kubectl delete -f k8s/tunnel-ngrok.yaml --ignore-not-found
```

### Clean Reset

```bash
# Remove all tunnel resources
kubectl delete configmap cloudflared-config ngrok-config -n ldap-jwt-app --ignore-not-found
kubectl delete secret tunnel-secrets ngrok-secrets cloudflared-credentials -n ldap-jwt-app --ignore-not-found
kubectl delete serviceaccount cloudflared -n ldap-jwt-app --ignore-not-found
kubectl delete service cloudflared-metrics ngrok-web-ui simple-tunnel-service -n ldap-jwt-app --ignore-not-found
```

## 📚 Additional Resources

### Architecture Diagram

```
Internet
   ↓
[Tunnel Provider]
   ↓
Kubernetes Cluster
   ↓
[Tunnel Pod] → [Frontend Service] → [Frontend Pods]
            ↓
            → [Backend Service] → [Backend Pods]
                               ↓
                               [LDAP Service]
```

### File Structure

```
k8s/
├── tunnel-cloudflared.yaml    # Cloudflare Tunnel deployment
├── tunnel-ngrok.yaml          # ngrok tunnel deployment
└── tunnel-localtunnel.yaml    # localtunnel deployment

scripts/
├── tunnel-setup.sh            # Linux/macOS management script
└── tunnel-setup.ps1           # Windows PowerShell script

TUNNEL-README.md               # This documentation
```

### WebSocket Configuration Details

All tunnel configurations include WebSocket support:

- **HTTP Upgrade headers** properly forwarded
- **Connection keep-alive** configured
- **Protocol switching** enabled
- **Binary data** transmission supported

### Production Considerations

1. **Use Cloudflare** for production sharing
2. **Configure custom domains** for branding
3. **Monitor tunnel metrics** via Kubernetes
4. **Set up alerts** for tunnel disconnections
5. **Consider rate limiting** at the application level
6. **Review security policies** for external access

---

## 🎉 Ready to Share!

Your LDAP-JWT authentication project is now ready to be shared with the world! Start with `localtunnel` for quick testing, then move to `Cloudflare` for production-ready sharing.

**Need help?** Check the troubleshooting section or review the logs with:
```bash
./scripts/tunnel-setup.sh logs <provider>
```

**Happy tunneling! 🚀** 