# Cloudflare Tunnel Setup for Batchivo

This guide explains how to configure Cloudflare Tunnel to expose your k3s cluster to the internet at batchivo.app.

## Prerequisites

- Cloudflare account with `batchivo.app` domain
- `cloudflared` installed on the machine running k3s
- k3s cluster running with Batchivo deployed

## Step 1: Install cloudflared

```bash
# On macOS
brew install cloudflare/cloudflare/cloudflared

# On Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

## Step 2: Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This will open a browser window to authorize cloudflared with your Cloudflare account.

## Step 3: Create a Tunnel

```bash
cloudflared tunnel create batchivo
```

This creates a tunnel and saves credentials to `~/.cloudflared/<tunnel-id>.json`.

Note the **Tunnel ID** from the output - you'll need it later.

## Step 4: Create Tunnel Configuration

Create the configuration file:

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Add the following configuration:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /Users/jonathan/.cloudflared/<your-tunnel-id>.json

ingress:
  # Frontend - batchivo.app
  - hostname: batchivo.app
    service: http://localhost:80

  # Backend API - api.batchivo.app
  - hostname: api.batchivo.app
    service: http://localhost:80

  # Catch-all rule (required)
  - service: http_status:404
```

**Note**: We're pointing to `localhost:80` because cloudflared will run on the same machine as k3s, and k3s's traefik ingress listens on port 80.

## Step 5: Configure DNS in Cloudflare

Route DNS to your tunnel:

```bash
cloudflared tunnel route dns batchivo batchivo.app
cloudflared tunnel route dns batchivo api.batchivo.app
```

Or manually in Cloudflare Dashboard:
1. Go to DNS settings for `batchivo.app`
2. Add CNAME record: `batchivo.app` → `<tunnel-id>.cfargotunnel.com`
3. Add CNAME record: `api.batchivo.app` → `<tunnel-id>.cfargotunnel.com`

## Step 6: Update K3s Ingress

Make sure your k3s ingress is listening for the correct hostnames. Check:

```bash
kubectl get ingress -n batchivo
```

The ingress should have rules for:
- `batchivo.app` → frontend service
- `api.batchivo.app` → backend service

## Step 7: Run the Tunnel

### Option A: Run in Foreground (Testing)

```bash
cloudflared tunnel run batchivo
```

### Option B: Run as System Service (Production)

Install as a system service:

```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

Check status:

```bash
sudo systemctl status cloudflared
```

View logs:

```bash
sudo journalctl -u cloudflared -f
```

## Step 8: Verify Deployment

1. **Check tunnel status** in Cloudflare Dashboard:
   - Go to Zero Trust → Access → Tunnels
   - You should see "batchivo" tunnel with status "HEALTHY"

2. **Test DNS resolution**:
   ```bash
   dig batchivo.app
   dig api.batchivo.app
   ```

3. **Test HTTP access**:
   ```bash
   curl https://batchivo.app
   curl https://api.batchivo.app/health
   ```

4. **Open in browser**:
   - https://batchivo.app (should show React frontend)
   - https://api.batchivo.app/docs (should show FastAPI docs)

## Troubleshooting

### Tunnel shows UNHEALTHY

Check cloudflared logs:
```bash
sudo journalctl -u cloudflared -f
```

Verify k3s ingress is running:
```bash
kubectl get pods -n kube-system | grep traefik
kubectl get svc -n kube-system traefik
```

### 502 Bad Gateway

- Check if k3s pods are running: `kubectl get pods -n batchivo`
- Check pod logs: `kubectl logs -f deployment/frontend -n batchivo`
- Verify service endpoints: `kubectl get endpoints -n batchivo`

### Connection Refused

- Make sure cloudflared is running on the same machine as k3s
- Check that ingress service points to `http://localhost:80`
- Verify traefik is listening: `sudo netstat -tulpn | grep :80`

## Security Notes

1. **SSL/TLS**: Cloudflare provides automatic SSL for your tunnel
2. **Firewall**: No need to open ports - tunnel is outbound-only
3. **Authentication**: Consider adding Cloudflare Access for admin routes
4. **Rate Limiting**: Configure in Cloudflare Dashboard → Security

## Architecture Diagram

```
[Internet Users]
       ↓
[Cloudflare Edge]
       ↓
[Cloudflare Tunnel (cloudflared)]
       ↓
[k3s Traefik Ingress :80]
       ↓
[k3s Services]
  ├─ frontend:8080
  └─ backend:8000
```

## Alternative: Direct Cloudflare to k3s

If cloudflared runs in a k3s pod instead:

```yaml
# cloudflare-tunnel-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: batchivo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      containers:
      - name: cloudflared
        image: cloudflare/cloudflared:latest
        args:
        - tunnel
        - --no-autoupdate
        - run
        - --token
        - <your-tunnel-token>
```

This approach runs cloudflared inside your cluster for better HA.

## Useful Commands

```bash
# List tunnels
cloudflared tunnel list

# Check tunnel info
cloudflared tunnel info batchivo

# Delete tunnel
cloudflared tunnel delete batchivo

# Test config
cloudflared tunnel ingress validate

# View ingress rules
cloudflared tunnel ingress list
```

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [k3s Traefik Configuration](https://docs.k3s.io/networking#traefik-ingress-controller)
