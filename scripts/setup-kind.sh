#!/bin/bash
# KubeNetLLM Kind Cluster Setup Script

set -e

echo "Setting up Kind cluster for KubeNetLLM experiments..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="kubenet-test"
CONFIG_FILE="config/kind-config.yaml"
KUBECONFIG_PATH="$HOME/.kube/config"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker Desktop.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check Kind
if ! command -v kind &> /dev/null; then
    echo -e "${RED}Kind is not installed. Please run ./scripts/setup-venv.sh first.${NC}"
    exit 1
fi

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl is not installed. Please install kubectl.${NC}"
    exit 1
fi

echo -e "${GREEN}Prerequisites check passed!${NC}"

# Delete existing cluster if it exists
if kind get clusters | grep -q "$CLUSTER_NAME"; then
    echo -e "${YELLOW}Deleting existing cluster '$CLUSTER_NAME'...${NC}"
    kind delete cluster --name "$CLUSTER_NAME"
fi

# Create new cluster
echo -e "${YELLOW}Creating Kind cluster '$CLUSTER_NAME'...${NC}"
kind create cluster --name "$CLUSTER_NAME" --config "$CONFIG_FILE"

# Wait for cluster to be ready
echo -e "${YELLOW}Waiting for cluster to be ready...${NC}"
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Create data directory
echo -e "${YELLOW}Creating data directory...${NC}"
mkdir -p data/knowledge_base
mkdir -p data/templates
mkdir -p experiments/results

# Install basic cluster components
echo -e "${YELLOW}Installing basic cluster components...${NC}"

# Install ingress controller
echo -e "${BLUE}Installing NGINX Ingress Controller...${NC}"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for ingress controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

# Install cert-manager
echo -e "${BLUE}Installing cert-manager...${NC}"
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=cert-manager \
  --timeout=300s

# Install Istio (optional, for service mesh scenarios)
if command -v istioctl &> /dev/null; then
    echo -e "${BLUE}Installing Istio...${NC}"
    istioctl install --set values.defaultRevision=default -y
    
    # Enable automatic sidecar injection
    kubectl label namespace default istio-injection=enabled
    
    # Wait for Istio to be ready
    kubectl wait --namespace istio-system \
      --for=condition=ready pod \
      --selector=app=istiod \
      --timeout=300s
else
    echo -e "${YELLOW}Istioctl not found. Skipping Istio installation.${NC}"
fi

# Create test namespaces
echo -e "${YELLOW}Creating test namespaces...${NC}"
kubectl create namespace kubenet-test || true
kubectl create namespace kubenet-staging || true
kubectl create namespace kubenet-prod || true

# Label namespaces for network policy testing
kubectl label namespace kubenet-test environment=test
kubectl label namespace kubenet-staging environment=staging
kubectl label namespace kubenet-prod environment=production

# Create RBAC for experiments
echo -e "${YELLOW}Setting up RBAC...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubenet-experimental
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubenet-experimental
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["apps"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["networking.k8s.io"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["security.istio.io"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["networking.istio.io"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubenet-experimental
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubenet-experimental
subjects:
- kind: ServiceAccount
  name: kubenet-experimental
  namespace: default
EOF

# Update kubeconfig context
echo -e "${YELLOW}Updating kubeconfig context...${NC}"
kubectl config use-context "kind-$CLUSTER_NAME"

# Verify cluster is working
echo -e "${YELLOW}Verifying cluster...${NC}"
kubectl get nodes
kubectl get pods --all-namespaces

echo -e "${GREEN}Kind cluster setup complete!${NC}"
echo ""
echo -e "${BLUE}Cluster Information:${NC}"
echo -e "${YELLOW}  Cluster Name: $CLUSTER_NAME${NC}"
echo -e "${YELLOW}  Context: kind-$CLUSTER_NAME${NC}"
echo -e "${YELLOW}  API Server: https://127.0.0.1:6443${NC}"
echo ""
echo -e "${BLUE}Installed Components:${NC}"
echo -e "${YELLOW}  ✓ NGINX Ingress Controller${NC}"
echo -e "${YELLOW}  ✓ cert-manager${NC}"
if command -v istioctl &> /dev/null; then
    echo -e "${YELLOW}  ✓ Istio Service Mesh${NC}"
fi
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Activate virtual environment: source activate_kubenet.sh"
echo "2. Configure API keys in .env file"
echo "3. Run experiments: python experiments/run_experiments.py" 