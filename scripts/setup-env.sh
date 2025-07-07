#!/bin/bash
# KubeNetLLM Environment Setup Script

set -e

echo "Setting up KubeNetLLM experimental environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}This script is designed for macOS. Please modify for your OS.${NC}"
    exit 1
fi

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Docker Desktop
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker Desktop for Mac.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check/Install Kind
if ! command -v kind &> /dev/null; then
    echo -e "${YELLOW}Installing Kind...${NC}"
    brew install kind
fi

# Check/Install kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}Installing kubectl...${NC}"
    brew install kubectl
fi

# Check/Install Helm
if ! command -v helm &> /dev/null; then
    echo -e "${YELLOW}Installing Helm...${NC}"
    brew install helm
fi

# Check/Install Istioctl
if ! command -v istioctl &> /dev/null; then
    echo -e "${YELLOW}Installing Istioctl...${NC}"
    curl -L https://istio.io/downloadIstio | sh -
    export PATH="$PATH:$HOME/.istioctl/bin"
fi

# Check/Install Ollama (optional)
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Installing Ollama...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
fi

# Create environment file
echo -e "${YELLOW}Creating environment configuration...${NC}"
cat > .env << EOF
# KubeNetLLM Environment Configuration
OPENAI_API_KEY=${OPENAI_API_KEY:-your_openai_api_key_here}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-your_anthropic_api_key_here}
KUBECONFIG=~/.kube/config
KUBECTL_CONTEXT=kind-kubenet-test
MCP_BROKER_HOST=localhost
MCP_BROKER_PORT=8080
MCP_WEBSOCKET_PORT=8081
OLLAMA_HOST=http://localhost:11434
EXPERIMENTS_OUTPUT_DIR=experiments/results
LOG_LEVEL=INFO
ENABLE_SECURITY_SCANNING=true
SECURITY_SCANNER_TYPE=kubesec
DEBUG=false
DEV_MODE=false
ENABLE_METRICS=true
METRICS_PORT=9090
DOCKER_HOST=unix:///var/run/docker.sock
EOF

echo -e "${GREEN}Environment configuration created in .env${NC}"
echo -e "${YELLOW}Please edit .env file and add your API keys before running experiments.${NC}"

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit .env file and add your API keys"
echo "2. Run: ./scripts/setup-kind.sh"
echo "3. Run: python experiments/run_experiments.py" 