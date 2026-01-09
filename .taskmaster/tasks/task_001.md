# Task ID: 1

**Title:** Deploy Authentik Infrastructure to k3s Cluster

**Status:** done

**Dependencies:** None

**Priority:** high

**Description:** Deploy Authentik PostgreSQL, Redis, server, and worker components to k3s cluster with proper ingress configuration

**Details:**

Deploy all Authentik components using existing k8s manifests in infrastructure/k8s/authentik/. Configure Cloudflare Tunnel ingress rule for auth.nozzly.app → authentik-server:9000. Verify database connectivity and health checks. The manifests already exist (postgres.yaml, redis.yaml, server.yaml) and should be applied in order. Ensure persistent storage for PostgreSQL and proper resource limits. Test accessibility at https://auth.nozzly.app after deployment.

**Test Strategy:**

Verify Authentik server is accessible at https://auth.nozzly.app, check pod status with kubectl get pods -n nozzly, test admin login at auth.nozzly.app/if/admin/, verify all health checks are passing, test database connectivity between Authentik server and postgres pods
