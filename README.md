# KubeNetLLM: Experimental Framework

An architectural framework for context-aware Kubernetes network configuration using LLMs and MCP.

## Overview

This repository contains the experimental implementation of KubeNetLLM as described in the paper "KubeNetLLM: An Architectural Framework for Context-Aware Kubernetes Network Configuration Using LLMs and MCP".

## Architecture

KubeNetLLM consists of four primary components:

1. **Natural Language Interface Engine**: Processes natural language requirements and converts them into structured requests
2. **Configuration Generator with MCP Integration**: Generates Kubernetes configurations using LLMs enhanced with MCP
3. **Hierarchical Validation Framework**: Multi-layer validation ensuring configuration correctness and security
4. **Intelligent Deployment Manager**: Orchestrates safe deployment of validated configurations

## Experimental Setup

### Prerequisites

- Docker Desktop for Mac
- Kind (Kubernetes in Docker)
- Python 3.9+
- OpenAI API key (for GPT-4 access)
- Ollama (for local LLM testing)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd kubenet

# Set up virtual environment and install dependencies
chmod +x scripts/setup-venv.sh
./scripts/setup-venv.sh

# Activate virtual environment
source activate_kubenet.sh

# Set up Kind cluster
chmod +x scripts/setup-kind.sh
./scripts/setup-kind.sh

# Configure API keys in .env file
# Edit .env and add your OpenAI/Anthropic API keys

# Start MCP broker
python src/mcp/broker.py
```

### Test Scenarios

The framework includes five test scenarios:

1. **Simple Web Application**: Basic three-tier web application
2. **Microservices with Service Mesh**: Complex microservices with Istio
3. **Multi-Environment Configuration**: Different configs for dev/staging/prod
4. **Security-Focused Deployment**: Zero-trust networking with mTLS
5. **Edge Case Handling**: Ambiguous requirements testing

### Running Experiments

```bash
# Run all experiments
python experiments/run_experiments.py

# Run specific scenario
python experiments/run_scenario.py --scenario simple_web_app

# Generate performance report
python experiments/generate_report.py
```

## Project Structure

```
kubenet/
├── src/
│   ├── core/                    # Core KubeNetLLM components
│   ├── mcp/                     # MCP broker and integrations
│   ├── validation/              # Hierarchical validation framework
│   └── deployment/              # Deployment manager
├── experiments/                 # Experimental framework
│   ├── scenarios/               # Test scenarios
│   ├── metrics/                 # Performance measurement
│   └── validation/              # Validation tests
├── config/                      # Configuration files
├── scripts/                     # Setup and utility scripts
└── docs/                        # Documentation
```

## Metrics and Validation

The framework measures:

- **Generation Time**: End-to-end configuration generation time
- **API Call Count**: Number of LLM API calls required
- **Token Usage**: Total tokens consumed
- **Validation Pass Rate**: Percentage of configurations passing validation
- **Resource Utilization**: CPU, memory, and network usage

## Contributing

This is an experimental framework for research purposes. Contributions are welcome through pull requests.

## License

MIT License - see LICENSE file for details. 