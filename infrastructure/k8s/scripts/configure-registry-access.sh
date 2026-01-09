#!/bin/bash
#
# Configure k3s nodes to allow HTTP registry access
# This script must be run WITH SSH access to the k3s nodes
#
# Usage: ./configure-registry-access.sh

set -euo pipefail

# Registry configuration
REGISTRY_HOST="192.168.98.138:30500"

# k3s nodes to configure
K3S_NODES=(
    "homelab@192.168.98.138"
    "homelab@192.168.98.128"
    "homelab@192.168.98.136"
    "homelab@192.168.98.141"
)

echo "=================================================="
echo "K3s HTTP Registry Configuration Script"
echo "=================================================="
echo ""
echo "This script will configure ${#K3S_NODES[@]} k3s nodes to allow"
echo "HTTP access to the registry at ${REGISTRY_HOST}"
echo ""

# Check if we have SSH access
echo "Testing SSH connectivity..."
for node in "${K3S_NODES[@]}"; do
    echo -n "  Checking ${node}... "
    if ssh -o ConnectTimeout=5 "${node}" "echo ok" &>/dev/null; then
        echo "✓"
    else
        echo "✗ FAILED"
        echo ""
        echo "ERROR: Cannot SSH to ${node}"
        echo "Please ensure:"
        echo "  1. SSH keys are configured"
        echo "  2. Node is reachable"
        echo "  3. User has sudo access"
        echo ""
        exit 1
    fi
done

echo ""
echo "All nodes are accessible. Proceeding with configuration..."
echo ""

# Function to configure a single node
configure_node() {
    local node=$1
    local node_name=$(echo "${node}" | cut -d'@' -f1)

    echo "Configuring ${node_name}..."

    # Create the registries.yaml configuration
    ssh "${node}" "cat <<EOF | sudo tee /etc/rancher/k3s/registries.yaml > /dev/null
mirrors:
  \"${REGISTRY_HOST}\":
    endpoint:
      - \"http://${REGISTRY_HOST}\"
configs:
  \"${REGISTRY_HOST}\":
    tls:
      insecure_skip_verify: true
EOF"

    if [ $? -eq 0 ]; then
        echo "  ✓ Configuration file created"
    else
        echo "  ✗ Failed to create configuration file"
        return 1
    fi

    # Restart k3s service
    echo "  Restarting k3s service..."
    ssh "${node}" sudo systemctl restart k3s

    if [ $? -eq 0 ]; then
        echo "  ✓ k3s service restarted"
    else
        echo "  ✗ Failed to restart k3s service"
        return 1
    fi

    # Wait for k3s to be ready
    echo "  Waiting for k3s to be ready..."
    sleep 5

    echo "  ✓ ${node_name} configured successfully"
    echo ""
}

# Configure all nodes
for node in "${K3S_NODES[@]}"; do
    configure_node "${node}"
done

echo "=================================================="
echo "Configuration Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Verify pods can now pull images:"
echo "     kubectl delete pods -n nozzly -l app=backend"
echo "     kubectl get pods -n nozzly -w"
echo ""
echo "  2. Check pod events for successful image pulls:"
echo "     kubectl describe pod -n nozzly <pod-name>"
echo ""
echo "  3. Monitor backend logs for migration execution:"
echo "     kubectl logs -f -n nozzly -l app=backend -c run-migrations"
echo ""
