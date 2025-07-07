#!/bin/bash
# KubeNetLLM Virtual Environment Setup Script

set -e

echo "Setting up KubeNetLLM virtual environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}This script is designed for macOS. Please modify for your OS.${NC}"
    exit 1
fi

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Python $required_version or higher is required. Found: $python_version${NC}"
    exit 1
fi

echo -e "${GREEN}Python version: $python_version ✓${NC}"

# Create virtual environment
VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Removing...${NC}"
    rm -rf "$VENV_DIR"
fi

echo -e "${YELLOW}Creating virtual environment...${NC}"
python3 -m venv "$VENV_DIR"

echo -e "${GREEN}Virtual environment created successfully!${NC}"

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}Dependencies installed successfully!${NC}"

# Create activation script
cat > activate_kubenet.sh << 'EOF'
#!/bin/bash
# KubeNetLLM Virtual Environment Activation Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Activating KubeNetLLM virtual environment...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Virtual environment not found. Run ./scripts/setup-venv.sh first.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

echo -e "${GREEN}KubeNetLLM virtual environment activated!${NC}"
echo -e "${BLUE}To deactivate, run: deactivate${NC}"
EOF

chmod +x activate_kubenet.sh

echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo -e "${BLUE}To activate the virtual environment in the future:${NC}"
echo -e "${YELLOW}  source activate_kubenet.sh${NC}"
echo ""
echo -e "${BLUE}Or manually:${NC}"
echo -e "${YELLOW}  source venv/bin/activate${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit .env file and add your API keys"
echo "2. Run: ./scripts/setup-kind.sh"
echo "3. Run: python experiments/run_experiments.py" 