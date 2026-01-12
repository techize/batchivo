#!/bin/bash
#
# Cluster Health Check Script
# Checks k3s cluster, tunnels, and external service accessibility
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_IP="192.168.98.138"
REGISTRY_PORT="30500"

# URLs to check (format: "url|description")
URLS=(
    "ci.techize.co.uk|Woodpecker CI"
    "argocd.techize.co.uk|ArgoCD"
    "batchivo.app|Batchivo Frontend"
    "api.batchivo.app/health|Batchivo Backend API"
    "auth.batchivo.app|Authentik SSO"
    "mystmereforge.co.uk|Mystmereforge Main"
    "shop.mystmereforge.co.uk|Mystmereforge Shop"
)

# Namespaces to check
NAMESPACES=("batchivo" "woodpecker" "registry" "argocd" "linkerd" "kube-system")

echo ""
echo "========================================"
echo "   K3s Cluster Health Check"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# Track issues
ISSUES=()

# ----------------------------------------
# 1. Cluster Connectivity
# ----------------------------------------
echo -e "${BLUE}[1/6] Cluster Connectivity${NC}"

if ping -c 1 -W 2 "$CLUSTER_IP" &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Cluster node reachable ($CLUSTER_IP)"
else
    echo -e "  ${RED}✗${NC} Cluster node unreachable ($CLUSTER_IP)"
    ISSUES+=("Cluster node $CLUSTER_IP is not reachable")
fi

if kubectl cluster-info &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} kubectl connected to cluster"
else
    echo -e "  ${RED}✗${NC} kubectl cannot connect to cluster"
    ISSUES+=("kubectl cannot connect to cluster")
    echo ""
    echo -e "${RED}Cannot proceed without cluster access${NC}"
    exit 1
fi

# ----------------------------------------
# 2. Node Status
# ----------------------------------------
echo ""
echo -e "${BLUE}[2/6] Node Status${NC}"

NOT_READY=$(kubectl get nodes --no-headers 2>/dev/null | grep -v "Ready" | wc -l | tr -d ' ')
TOTAL_NODES=$(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')

if [ "$NOT_READY" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} All $TOTAL_NODES nodes are Ready"
else
    echo -e "  ${RED}✗${NC} $NOT_READY of $TOTAL_NODES nodes are NOT Ready"
    ISSUES+=("$NOT_READY nodes are not ready")
    kubectl get nodes --no-headers 2>/dev/null | grep -v "Ready" | while read line; do
        echo -e "    ${YELLOW}→${NC} $line"
    done
fi

# ----------------------------------------
# 3. Pod Status by Namespace
# ----------------------------------------
echo ""
echo -e "${BLUE}[3/6] Pod Status${NC}"

for NS in "${NAMESPACES[@]}"; do
    if ! kubectl get namespace "$NS" &>/dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Namespace $NS does not exist"
        continue
    fi

    PROBLEM_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -vE "Running|Completed" | wc -l | tr -d ' ')
    TOTAL_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | wc -l | tr -d ' ')

    if [ "$TOTAL_PODS" -eq 0 ]; then
        echo -e "  ${YELLOW}⚠${NC} $NS: No pods"
    elif [ "$PROBLEM_PODS" -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} $NS: All $TOTAL_PODS pods healthy"
    else
        echo -e "  ${RED}✗${NC} $NS: $PROBLEM_PODS of $TOTAL_PODS pods have issues"
        ISSUES+=("$NS: $PROBLEM_PODS pods with issues")
        kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -vE "Running|Completed" | while read line; do
            echo -e "    ${YELLOW}→${NC} $line"
        done
    fi
done

# ----------------------------------------
# 4. Registry Status
# ----------------------------------------
echo ""
echo -e "${BLUE}[4/6] Container Registry${NC}"

REGISTRY_URL="http://$CLUSTER_IP:$REGISTRY_PORT"
if curl -s --max-time 5 "$REGISTRY_URL/v2/_catalog" &>/dev/null; then
    REPO_COUNT=$(curl -s --max-time 5 "$REGISTRY_URL/v2/_catalog" 2>/dev/null | grep -o '"repositories":\[.*\]' | grep -o ',' | wc -l | tr -d ' ')
    REPOS=$(curl -s --max-time 5 "$REGISTRY_URL/v2/_catalog" 2>/dev/null)

    if echo "$REPOS" | grep -q '"repositories":\[\]'; then
        echo -e "  ${RED}✗${NC} Registry accessible but EMPTY (data loss?)"
        ISSUES+=("Registry is empty - images need to be rebuilt")
    else
        echo -e "  ${GREEN}✓${NC} Registry accessible with images"
        echo -e "    ${NC}Repositories: $REPOS"
    fi
else
    echo -e "  ${RED}✗${NC} Registry not accessible at $REGISTRY_URL"
    ISSUES+=("Container registry not accessible")
fi

# ----------------------------------------
# 5. Cloudflare Tunnel Status
# ----------------------------------------
echo ""
echo -e "${BLUE}[5/6] Cloudflare Tunnel${NC}"

TUNNEL_PODS=$(kubectl get pods -n batchivo -l app=cloudflared --no-headers 2>/dev/null | grep "Running" | wc -l | tr -d ' ')
if [ "$TUNNEL_PODS" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Cloudflared: $TUNNEL_PODS pod(s) running"

    # Check tunnel registration from logs
    if kubectl logs -n batchivo -l app=cloudflared --tail=50 2>/dev/null | grep -q "Registered tunnel connection"; then
        echo -e "  ${GREEN}✓${NC} Tunnel connections registered"
    else
        echo -e "  ${YELLOW}⚠${NC} Could not verify tunnel registration"
    fi
else
    echo -e "  ${RED}✗${NC} Cloudflared: No running pods"
    ISSUES+=("Cloudflared tunnel pods not running")
fi

# ----------------------------------------
# 6. External URL Accessibility
# ----------------------------------------
echo ""
echo -e "${BLUE}[6/6] External URLs${NC}"

for ENTRY in "${URLS[@]}"; do
    URL=$(echo "$ENTRY" | cut -d'|' -f1)
    SERVICE=$(echo "$ENTRY" | cut -d'|' -f2)

    # Check DNS first
    DOMAIN=$(echo "$URL" | cut -d'/' -f1)
    if ! dig +short "$DOMAIN" 2>/dev/null | grep -q .; then
        echo -e "  ${RED}✗${NC} $SERVICE ($URL)"
        echo -e "    ${YELLOW}→${NC} DNS not resolving"
        ISSUES+=("$SERVICE: DNS not resolving for $DOMAIN")
        continue
    fi

    # Check HTTP response
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://$URL" 2>/dev/null || echo "000")

    case "$HTTP_CODE" in
        200|301|302|303|307|308)
            echo -e "  ${GREEN}✓${NC} $SERVICE ($URL) - HTTP $HTTP_CODE"
            ;;
        401|403)
            echo -e "  ${GREEN}✓${NC} $SERVICE ($URL) - HTTP $HTTP_CODE (auth required)"
            ;;
        502|503|504)
            echo -e "  ${RED}✗${NC} $SERVICE ($URL) - HTTP $HTTP_CODE (backend down)"
            ISSUES+=("$SERVICE: HTTP $HTTP_CODE - backend unavailable")
            ;;
        000)
            echo -e "  ${RED}✗${NC} $SERVICE ($URL) - Connection failed"
            ISSUES+=("$SERVICE: Connection failed")
            ;;
        *)
            echo -e "  ${YELLOW}⚠${NC} $SERVICE ($URL) - HTTP $HTTP_CODE"
            ;;
    esac
done

# ----------------------------------------
# Summary
# ----------------------------------------
echo ""
echo "========================================"
echo "   Summary"
echo "========================================"

if [ ${#ISSUES[@]} -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Cluster is healthy.${NC}"
else
    echo -e "${RED}Found ${#ISSUES[@]} issue(s):${NC}"
    echo ""
    for i in "${!ISSUES[@]}"; do
        echo -e "  ${YELLOW}$((i+1)).${NC} ${ISSUES[$i]}"
    done
fi

echo ""
echo "Check completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Exit with error code if issues found
[ ${#ISSUES[@]} -eq 0 ] && exit 0 || exit 1
