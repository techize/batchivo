---
sidebar_position: 1
---

# Self-Hosting Overview

Deploy Batchivo on your own infrastructure for complete control over your data.

## Deployment Options

| Method | Complexity | Best For |
|--------|------------|----------|
| [Docker Compose](/docs/self-hosting/docker-compose) | Low | Single server, home lab |
| [Kubernetes](/docs/self-hosting/kubernetes) | Medium | Multi-node, production |
| Manual | High | Custom environments |

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Reverse Proxy                  │
│              (Traefik/Caddy/nginx)              │
└─────────────────┬───────────────┬───────────────┘
                  │               │
         ┌────────▼────────┐ ┌───▼────────┐
         │    Frontend     │ │   Backend   │
         │   (React SPA)   │ │  (FastAPI)  │
         └────────────────┘ └──────┬──────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
              ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
              │ PostgreSQL│ │   Redis   │ │  Storage  │
              │           │ │           │ │  (Local)  │
              └───────────┘ └───────────┘ └───────────┘
```

## System Requirements

### Minimum

- 2 CPU cores
- 2GB RAM
- 10GB disk space

### Recommended

- 4 CPU cores
- 4GB RAM
- 50GB SSD

## TLS/SSL

Always use HTTPS in production. Options:

### Reverse Proxy (Recommended)

Use Traefik, Caddy, or nginx with automatic TLS:

**Caddy example:**
```
batchivo.example.com {
    reverse_proxy frontend:80
}

api.batchivo.example.com {
    reverse_proxy backend:8000
}
```

### Cloudflare Tunnel

For home lab deployments without port forwarding:

```bash
# Install cloudflared
brew install cloudflared  # or apt install cloudflared

# Create tunnel
cloudflared tunnel login
cloudflared tunnel create batchivo

# Configure (config.yml)
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: batchivo.example.com
    service: http://localhost:80
  - service: http_status:404

# Run
cloudflared tunnel run batchivo
```

## Security Recommendations

1. **Change default passwords** - Never use default credentials
2. **Use TLS** - Always use HTTPS in production
3. **Firewall** - Only expose ports 80/443
4. **Backups** - Test restoration regularly
5. **Updates** - Keep images updated for security patches

## Next Steps

- [Docker Compose deployment](/docs/self-hosting/docker-compose)
- [Environment variables](/docs/self-hosting/environment-variables)
- [Backup & restore](/docs/self-hosting/backup-restore)
