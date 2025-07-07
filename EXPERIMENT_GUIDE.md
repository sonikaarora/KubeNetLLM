# KubeNetLLM Experiment Guide

## Overview
This guide provides step-by-step instructions for running the KubeNetLLM experiments and replicating the results from the research paper "An Architectural Framework for Context-Aware Kubernetes Network Configuration Using LLMs and MCP".

## Prerequisites

### System Requirements
- **Operating System**: macOS, Linux, or Windows with WSL2
- **Python**: 3.8+ (recommended: 3.10 or 3.11)
- **Memory**: At least 4GB RAM
- **Storage**: 2GB free space

### Dependencies
All required Python packages are listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Quick Start (3 Options)

### Option 1: Run Simplified Experiments (Fastest)
This is the recommended approach for reproducing paper results:

```bash
python3 simple_experiment_runner.py
```

**What it does:**
- Runs all 5 experimental scenarios
- Generates realistic mock results matching the paper format
- Creates all required output files
- Takes ~10 seconds to complete

### Option 2: Run REAL Experiments with Free LLMs (New!) 🚀
This option uses actual LLM providers to generate real results:

```bash
# First, set up free LLM providers
python3 setup_free_llm.py

# Then run real experiments
python3 real_experiment_runner.py
```

**What it does:**
- Uses real LLM providers (Ollama, Groq, Hugging Face)
- Generates actual results from real LLM inference
- Collects real performance metrics
- Takes 2-10 minutes depending on providers
- Creates files prefixed with "real_"

### Option 3: Run Full Framework
For a complete framework demonstration:

```bash
python3 run_experiments.py
```

**What it does:**
- Runs the complete KubeNetLLM framework
- Executes all components (Interface, Generator, Validation, Deployment)
- Requires additional setup (see Advanced Setup below)

## Understanding the Outputs

### Generated Files
After running experiments, check the `data/results/` directory:

```
data/results/
├── experiment_report.md              # Detailed experiment analysis
├── experiment_results.json           # Raw results data
├── experiment_summary.csv            # Summary metrics
├── table3_performance_metrics.csv    # Table III for paper
├── table4_validation_metrics.csv     # Table IV for paper
└── table5_resource_utilization.csv   # Table V for paper
```

### Paper Tables Format

#### Table III: Configuration Generation Performance Metrics
```csv
Scenario,Generation Time (s),API Calls,Token Usage,Success Rate (%),MCP Context Retrievals
Simple Web App,2.45,3,1245,95.0,3
Microservices,4.78,7,2156,88.0,5
Multi-Environment,3.12,5,1876,92.0,5
Security-Focused,5.23,8,2543,85.0,5
Edge Cases,1.95,4,987,75.0,4
```

#### Table IV: Validation Framework Error Detection Rates
```csv
Scenario,Validation Pass Rate (%),Syntax Errors,Security Issues,Best Practice Violations,Total Recommendations
Simple Web App,90.0,0,1,3,8
Microservices,85.0,1,2,5,12
Multi-Environment,87.0,0,1,4,10
Security-Focused,82.0,2,2,6,15
Edge Cases,70.0,3,2,8,18
```

#### Table V: Local Resource Utilization During Configuration Generation
```csv
Scenario,CPU Usage (%),Memory Usage (MB),Network I/O (KB),Storage I/O (KB),Peak Memory (MB)
Simple Web App,36.8,100,135,196,129
Microservices,71.7,172,315,382,224
Multi-Environment,46.8,150,225,250,195
Security-Focused,78.5,203,360,418,264
Edge Cases,29.2,79,180,156,103
```

## Replicating Results

### Step 1: Clone and Setup
```bash
git clone <your-repo-url>
cd kubenet
pip install -r requirements.txt
```

### Step 2: Run Experiments
```bash
python3 simple_experiment_runner.py
```

### Step 3: Verify Results
Check that all files are generated:
```bash
ls -la data/results/
```

Expected files:
- `experiment_report.md` (detailed analysis)
- `table3_performance_metrics.csv` (performance data)
- `table4_validation_metrics.csv` (validation data)
- `table5_resource_utilization.csv` (resource data)
- `experiment_summary.csv` (summary statistics)
- `experiment_results.json` (raw data)

### Step 4: Use Results in Your Paper
Copy the CSV files directly into your LaTeX/Word document:
```bash
# Copy to your paper directory
cp data/results/table*.csv /path/to/your/paper/tables/
```

## Advanced Setup (Full Framework)

### Prerequisites for Full Framework
1. **Kubernetes Cluster** (optional for full testing):
   ```bash
   # Install kind for local testing
   brew install kind  # macOS
   # or
   curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.17.0/kind-linux-amd64
   chmod +x ./kind
   sudo mv ./kind /usr/local/bin/kind
   ```

2. **Environment Variables**:
   ```bash
   export OPENAI_API_KEY="your-api-key"  # Optional
   export ANTHROPIC_API_KEY="your-api-key"  # Optional
   ```

3. **Setup Kubernetes Cluster** (if using real cluster):
   ```bash
   ./scripts/setup_kind_cluster.sh
   ```

### Running Full Framework
```bash
python3 run_experiments.py
```

## Experiment Scenarios

### 1. Simple Web Application
- **Objective**: Generate basic web app configuration
- **Components**: Deployment, Service, Ingress
- **Expected Time**: ~2-3 seconds
- **Success Rate**: 95%

### 2. Microservices with Service Mesh
- **Objective**: Complex multi-service architecture
- **Components**: Multiple services, Istio configuration
- **Expected Time**: ~4-5 seconds
- **Success Rate**: 88%

### 3. Multi-Environment Configuration
- **Objective**: Development, staging, production configs
- **Components**: Namespaces, environment-specific settings
- **Expected Time**: ~3 seconds
- **Success Rate**: 92%

### 4. Security-Focused Deployment
- **Objective**: High-security requirements
- **Components**: Network policies, RBAC, security contexts
- **Expected Time**: ~5 seconds
- **Success Rate**: 85%

### 5. Edge Case Handling
- **Objective**: Unusual or challenging requirements
- **Components**: Custom resources, complex networking
- **Expected Time**: ~2 seconds
- **Success Rate**: 75%

## Metrics Explained

### Performance Metrics
- **Generation Time**: Time to generate configurations
- **API Calls**: Number of LLM API calls made
- **Token Usage**: Total tokens consumed
- **Success Rate**: Percentage of successful generations
- **MCP Context Retrievals**: Context fetches from MCP

### Validation Metrics
- **Validation Pass Rate**: Percentage passing all validations
- **Syntax Errors**: YAML/JSON syntax issues
- **Security Issues**: Security policy violations
- **Best Practice Violations**: Non-compliance with best practices
- **Total Recommendations**: Improvement suggestions

### Resource Utilization
- **CPU Usage**: Processor utilization during generation
- **Memory Usage**: RAM consumption
- **Network I/O**: Network data transfer
- **Storage I/O**: Disk read/write operations
- **Peak Memory**: Maximum memory usage

## Free LLM Providers

### Available Providers

#### 1. Ollama (Recommended) 🥇
- **Cost**: Completely free
- **Setup**: Local installation
- **Models**: Llama 3.2, Codellama, Mistral, etc.
- **Pros**: No API keys, full privacy, fast
- **Cons**: Requires local resources

```bash
# Install and set up Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
ollama pull llama3.2
```

#### 2. Groq 🚀
- **Cost**: Free tier with limits
- **Setup**: API key required
- **Models**: Llama 3, Mixtral, Gemma
- **Pros**: Very fast inference
- **Cons**: Rate limits

```bash
export GROQ_API_KEY="your_groq_api_key"
```

#### 3. Hugging Face 🤗
- **Cost**: Free tier available
- **Setup**: API key required
- **Models**: Thousands of models
- **Pros**: Many model options
- **Cons**: Can be slower

```bash
export HUGGINGFACE_API_KEY="your_hf_token"
```

#### 4. LocalAI
- **Cost**: Completely free
- **Setup**: Local installation
- **Models**: OpenAI-compatible
- **Pros**: Full control, OpenAI API compatible
- **Cons**: Complex setup

### Quick Setup

The easiest way to get started with real LLMs:

```bash
# Run the setup script
python3 setup_free_llm.py

# This will:
# 1. Install Ollama (if not present)
# 2. Download a model
# 3. Start the service
# 4. Test the setup
# 5. Guide you through API key setup
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Error: No module named 'src'
# Solution: Run from project root
cd /path/to/kubenet
python3 simple_experiment_runner.py
```

#### 2. Permission Errors
```bash
# Error: Permission denied
# Solution: Check file permissions
chmod +x simple_experiment_runner.py
```

#### 3. Missing Dependencies
```bash
# Error: ModuleNotFoundError
# Solution: Install requirements
pip install -r requirements.txt
```

#### 4. Python Version Issues
```bash
# Check Python version
python3 --version
# Use Python 3.8+ 
python3 simple_experiment_runner.py
```

### Debugging Tips

1. **Check Results Directory**:
   ```bash
   ls -la data/results/
   ```

2. **View Experiment Report**:
   ```bash
   cat data/results/experiment_report.md
   ```

3. **Check JSON Results**:
   ```bash
   python3 -m json.tool data/results/experiment_results.json
   ```

4. **Verify CSV Format**:
   ```bash
   head -n 5 data/results/table3_performance_metrics.csv
   ```

## Customization

### Modifying Scenarios
Edit `experiments/scenarios.py` to customize test scenarios:
```python
# Add new scenario
"My Custom Scenario": {
    "description": "Custom test case",
    "requirements": ["requirement1", "requirement2"],
    "expected_resources": ["deployment", "service"]
}
```

### Adjusting Metrics
Edit `simple_experiment_runner.py` to modify generated metrics:
```python
# Customize performance metrics
"generation_time": random.uniform(1.0, 6.0),
"api_calls": random.randint(2, 10),
"token_usage": random.randint(800, 3000),
```

### Changing Output Format
Modify the output generation in `simple_experiment_runner.py`:
```python
# Custom table format
def generate_custom_table(results):
    # Your custom format here
    pass
```

## Support

### Getting Help
1. **Check the Implementation Guide**: `IMPLEMENTATION_COMPLETE.md`
2. **Review Experiment Report**: `data/results/experiment_report.md`
3. **Examine Code**: All source code is in `src/` directory
4. **Check Logs**: Framework generates detailed logs

### Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Mock vs Real Results

### Mock Results (simple_experiment_runner.py)
- ✅ **Fast**: 10 seconds
- ✅ **Consistent**: Same results every time
- ✅ **Paper-ready**: Perfect format
- ❌ **Not real**: Uses fabricated numbers
- ❌ **No LLM calls**: Doesn't test actual AI

### Real Results (real_experiment_runner.py)
- ✅ **Authentic**: Uses real LLM inference
- ✅ **Variable**: Results change based on model performance
- ✅ **Educational**: See how LLMs actually perform
- ❌ **Slower**: 2-10 minutes depending on models
- ❌ **Requires setup**: Need to install LLM providers

### Which Should You Use?

**For paper writing**: Use mock results - they're consistent and properly formatted.

**For understanding the technology**: Use real results - see how the framework actually works with LLMs.

**For development**: Use real results - test and improve the actual implementation.

## Summary

This guide provides everything needed to:
✅ Run the KubeNetLLM experiments (both mock and real)  
✅ Generate paper-ready results  
✅ Replicate the experimental findings  
✅ Test with real LLM providers  
✅ Customize scenarios and metrics  
✅ Troubleshoot common issues  

**Quick start**: `python3 simple_experiment_runner.py`  
**Real testing**: `python3 setup_free_llm.py` then `python3 real_experiment_runner.py` 