# Batchivo Network Policies

Network policies to restrict pod communication and external access in the batchivo namespace.

## Architecture Overview

```
                    [Internet]
                        |
                   [Traefik]
                   /       \
              [Frontend]  [Backend]
                             |
               +-------------+-------------+
               |             |             |
          [PostgreSQL]   [Redis]       [MinIO]
```

## Traffic Flow

### Allowed Ingress
- **Frontend**: Traefik (port 8080)
- **Backend**: Traefik (port 8000)
- **PostgreSQL**: Backend only (port 5432)
- **Redis**: Backend only (port 6379)
- **MinIO**: Backend and admin jobs (ports 9000, 9001)

### Allowed Egress
- **All pods**: DNS (kube-system, port 53)
- **Backend**: PostgreSQL, Redis, MinIO (in-namespace)
- **Backend**: External HTTPS (port 443) for Square API, Brevo, Authentik
- **PostgreSQL, Redis, MinIO**: No egress (data stores)

## Deployment

### Using Kustomize (Recommended)
```bash
kubectl apply -k infrastructure/k8s/network-policies/
```

### Manual Apply (In Order)
```bash
kubectl apply -f infrastructure/k8s/network-policies/00-default-deny.yaml
kubectl apply -f infrastructure/k8s/network-policies/01-allow-dns.yaml
kubectl apply -f infrastructure/k8s/network-policies/10-frontend-policy.yaml
kubectl apply -f infrastructure/k8s/network-policies/20-backend-policy.yaml
kubectl apply -f infrastructure/k8s/network-policies/30-postgres-policy.yaml
kubectl apply -f infrastructure/k8s/network-policies/40-redis-policy.yaml
kubectl apply -f infrastructure/k8s/network-policies/50-minio-policy.yaml
```

## Verification

### Check Policies Are Applied
```bash
kubectl get networkpolicies -n batchivo
```

Expected output:
```
NAME                 POD-SELECTOR   AGE
default-deny-all     <none>         1m
allow-dns-egress     <none>         1m
frontend-policy      app=frontend   1m
backend-policy       app=backend    1m
postgres-policy      app=postgres   1m
redis-policy         app=redis      1m
minio-policy         app=minio      1m
```

### Test Connectivity (from a debug pod)
```bash
# Create a debug pod
kubectl run netpol-test --rm -it --image=nicolaka/netshoot -n batchivo -- /bin/bash

# Test allowed connections
curl -v http://backend:8000/health   # Should work
curl -v http://postgres:5432         # Should fail (not backend pod)
curl -v http://redis:6379            # Should fail (not backend pod)

# Test DNS resolution
nslookup backend.batchivo.svc.cluster.local  # Should work
```

### Test from Backend Pod
```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -n batchivo -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Test internal connectivity
kubectl exec -n batchivo $BACKEND_POD -- curl -v http://postgres:5432   # Should connect
kubectl exec -n batchivo $BACKEND_POD -- curl -v http://redis:6379     # Should connect
kubectl exec -n batchivo $BACKEND_POD -- curl -v http://minio:9000     # Should connect

# Test external connectivity
kubectl exec -n batchivo $BACKEND_POD -- curl -v https://connect.squareup.com  # Should work
```

## Troubleshooting

### Pods Can't Resolve DNS
Check that the kube-system namespace has the correct label:
```bash
kubectl get namespace kube-system -o jsonpath='{.metadata.labels}'
```

If `kubernetes.io/metadata.name: kube-system` is missing, the DNS policy won't match.

### Backend Can't Reach External APIs
The backend policy allows HTTPS (443) to any external IP. If Authentik or other services are on private IPs, you may need to adjust the `except` CIDR blocks in `20-backend-policy.yaml`.

### Health Checks Failing
Ensure kubelet can reach pods. The policies include allowances for kube-system namespace.

## CNI Requirements

Network policies require a CNI that supports them:
- **Calico**: Full support
- **Cilium**: Full support
- **Weave**: Full support
- **Flannel**: No support (requires Calico or Canal overlay)

Check your CNI:
```bash
kubectl get pods -n kube-system | grep -E 'calico|cilium|weave'
```

## Security Notes

1. **Default Deny**: All traffic is denied unless explicitly allowed
2. **Private IPs Blocked**: Backend egress excludes RFC1918 ranges to prevent lateral movement
3. **Port-Specific**: Only required ports are opened
4. **Namespace-Scoped**: Policies only affect batchivo namespace

## External Services Reference

Backend needs HTTPS access to:
- **Square API**: `connect.squareup.com`, `connect.squareupsandbox.com`
- **Brevo/Sendinblue**: `api.brevo.com`
- **Authentik**: Your Authentik instance URL
- **Container Registry**: `registry.techize.co.uk` (for image pulls via containerd, handled outside NetworkPolicy)
