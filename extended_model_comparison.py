#!/usr/bin/env python3
"""
Extended Multi-Model Comparison for KubeNetLLM
Tests more models to provide comprehensive comparison
"""

import asyncio
import json
import time
import os
from typing import Dict, List, Any, Optional
import requests
import subprocess
from dataclasses import dataclass, field

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@dataclass
class ModelTestResult:
    """Result from testing a specific model"""
    model: str
    scenario: str
    success: bool
    generation_time: float
    tokens_used: int
    yaml_quality: str
    error: Optional[str] = None


class ExtendedModelComparison:
    """Extended model comparison with more models"""
    
    def __init__(self):
        self.models_to_test = [
            # Currently installed
            "llama3.2:3b",
            "codellama:latest",
            
            # Popular models to test (will be installed)
            "llama3.1:8b",
            "mistral:7b",
            "phi3:mini",
            "qwen2:7b",
            "gemma2:9b",
        ]
        
        self.scenarios = [
            "Simple Web App",
            "Microservices",
            "Multi-Environment",
            "Security-Focused",
            "Edge Cases"
        ]
        
        self.results = []
        
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_installed_models(self) -> List[str]:
        """Get list of installed models"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            
            installed = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    installed.append(model_name)
            
            return installed
        except Exception as e:
            logger.error(f"Failed to get installed models: {e}")
            return []
    
    def install_model(self, model: str) -> bool:
        """Install a model if not already installed"""
        try:
            logger.info(f"📥 Installing model: {model}")
            
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully installed: {model}")
                return True
            else:
                logger.error(f"❌ Failed to install {model}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout installing {model}")
            return False
        except Exception as e:
            logger.error(f"❌ Error installing {model}: {e}")
            return False
    
    def get_scenario_prompt(self, scenario: str) -> str:
        """Get prompt for a specific scenario"""
        prompts = {
            "Simple Web App": """
Generate a complete Kubernetes YAML configuration for a simple web application with the following requirements:
- A deployment with an nginx container
- A service to expose the application
- Use port 80
- Set replicas to 2
- Include proper labels and selectors

Return only valid YAML configuration.
""",
            "Microservices": """
Generate a complete Kubernetes YAML configuration for a microservices architecture with:
- A frontend service (nginx)
- A backend service (node.js API)
- A database service (postgres)
- Proper networking between services
- ConfigMap for environment variables
- Secrets for database credentials

Return only valid YAML configuration.
""",
            "Multi-Environment": """
Generate Kubernetes YAML configuration for a multi-environment setup with:
- Deployment for staging and production
- Different resource limits for each environment
- Environment-specific ConfigMaps
- Proper namespacing
- Service accounts

Return only valid YAML configuration.
""",
            "Security-Focused": """
Generate a security-focused Kubernetes YAML configuration with:
- SecurityContext with non-root user
- NetworkPolicy for traffic restrictions
- PodSecurityPolicy or SecurityContext constraints
- Resource limits and requests
- Read-only filesystem where possible

Return only valid YAML configuration.
""",
            "Edge Cases": """
Generate Kubernetes YAML configuration for edge cases including:
- InitContainers for setup
- Sidecar containers for logging
- Volume mounts and persistent storage
- Liveness and readiness probes
- Custom resource definitions

Return only valid YAML configuration.
"""
        }
        return prompts.get(scenario, "Generate a basic Kubernetes YAML configuration.")
    
    async def test_model(self, model: str, scenario: str) -> ModelTestResult:
        """Test a specific model on a scenario"""
        start_time = time.time()
        
        try:
            prompt = self.get_scenario_prompt(scenario)
            
            # Call Ollama API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 2048
                    }
                },
                timeout=120
            )
            
            if response.status_code != 200:
                return ModelTestResult(
                    model=model,
                    scenario=scenario,
                    success=False,
                    generation_time=time.time() - start_time,
                    tokens_used=0,
                    yaml_quality="Failed",
                    error=f"API error: {response.status_code}"
                )
            
            result = response.json()
            generated_content = result.get("response", "")
            generation_time = time.time() - start_time
            
            # Analyze the response
            success = self.analyze_yaml_quality(generated_content)
            tokens_used = len(generated_content.split()) + len(prompt.split())
            
            quality = "Valid YAML" if success else "Invalid YAML"
            
            return ModelTestResult(
                model=model,
                scenario=scenario,
                success=success,
                generation_time=generation_time,
                tokens_used=tokens_used,
                yaml_quality=quality
            )
            
        except Exception as e:
            return ModelTestResult(
                model=model,
                scenario=scenario,
                success=False,
                generation_time=time.time() - start_time,
                tokens_used=0,
                yaml_quality="Error",
                error=str(e)
            )
    
    def analyze_yaml_quality(self, content: str) -> bool:
        """Analyze if the generated content contains valid YAML"""
        try:
            import yaml
            
            # Extract YAML blocks
            yaml_blocks = []
            lines = content.split('\n')
            in_yaml_block = False
            current_block = []
            
            for line in lines:
                if line.strip().startswith('```yaml') or line.strip().startswith('```'):
                    if in_yaml_block:
                        # End of block
                        yaml_blocks.append('\n'.join(current_block))
                        current_block = []
                        in_yaml_block = False
                    else:
                        # Start of block
                        in_yaml_block = True
                elif in_yaml_block:
                    current_block.append(line)
                elif line.strip().startswith('apiVersion:'):
                    # Direct YAML without code blocks
                    yaml_blocks.append(content)
                    break
            
            # If we were still in a block, add it
            if in_yaml_block and current_block:
                yaml_blocks.append('\n'.join(current_block))
            
            # Try to parse each YAML block
            for block in yaml_blocks:
                try:
                    yaml.safe_load_all(block)
                    return True
                except:
                    continue
            
            return False
            
        except Exception:
            return False
    
    async def run_extended_comparison(self) -> Dict[str, Any]:
        """Run extended model comparison"""
        logger.info("🚀 Starting Extended Multi-Model Comparison")
        logger.info("=" * 80)
        
        if not self.check_ollama_available():
            logger.error("❌ Ollama is not available")
            return {"error": "Ollama not available"}
        
        # Get currently installed models
        installed_models = self.get_installed_models()
        logger.info(f"📋 Currently installed models: {installed_models}")
        
        # Install missing models (limit to a few for testing)
        models_to_install = [
            "llama3.1:8b",
            "mistral:7b", 
            "phi3:mini"
        ]
        
        for model in models_to_install:
            if model not in installed_models:
                logger.info(f"📥 Installing {model}...")
                if self.install_model(model):
                    installed_models.append(model)
                else:
                    logger.warning(f"⚠️ Failed to install {model}, skipping")
        
        # Test available models
        available_models = [m for m in self.models_to_test if m in installed_models]
        logger.info(f"🤖 Testing models: {available_models}")
        
        results = {
            "timestamp": time.time(),
            "models_tested": available_models,
            "scenarios": self.scenarios,
            "model_results": {},
            "summary": {}
        }
        
        # Test each model
        for model in available_models:
            logger.info(f"🤖 Testing model: {model}")
            results["model_results"][model] = {}
            
            model_success_count = 0
            model_total_time = 0
            model_total_tokens = 0
            
            for scenario in self.scenarios:
                logger.info(f"  📋 Testing scenario: {scenario}")
                
                test_result = await self.test_model(model, scenario)
                results["model_results"][model][scenario] = {
                    "success": test_result.success,
                    "generation_time": test_result.generation_time,
                    "tokens_used": test_result.tokens_used,
                    "yaml_quality": test_result.yaml_quality,
                    "error": test_result.error
                }
                
                if test_result.success:
                    model_success_count += 1
                    
                model_total_time += test_result.generation_time
                model_total_tokens += test_result.tokens_used
                
                logger.info(f"    ✅ Success: {test_result.success}")
                logger.info(f"    ⏱️  Time: {test_result.generation_time:.2f}s")
                logger.info(f"    🔢 Tokens: {test_result.tokens_used}")
        
            # Calculate model summary
            success_rate = (model_success_count / len(self.scenarios)) * 100
            avg_time = model_total_time / len(self.scenarios)
            avg_tokens = model_total_tokens / len(self.scenarios)
            
            results["model_results"][model]["summary"] = {
                "success_rate": success_rate,
                "avg_generation_time": avg_time,
                "avg_tokens_used": avg_tokens,
                "total_scenarios": len(self.scenarios),
                "successful_scenarios": model_success_count
            }
            
            logger.info(f"📊 {model} Summary:")
            logger.info(f"   Success Rate: {success_rate:.1f}%")
            logger.info(f"   Avg Time: {avg_time:.2f}s")
            logger.info(f"   Avg Tokens: {avg_tokens:.0f}")
        
        # Generate overall summary
        results["summary"] = self.generate_summary(results["model_results"])
        
        # Save results
        os.makedirs("data/results", exist_ok=True)
        results_file = f"data/results/extended_model_comparison_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📄 Results saved to: {results_file}")
        
        return results
    
    def generate_summary(self, model_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of all model results"""
        summary = {
            "best_model": None,
            "worst_model": None,
            "performance_ranking": [],
            "key_insights": []
        }
        
        # Rank models by success rate
        model_rankings = []
        for model, results in model_results.items():
            if "summary" in results:
                model_rankings.append({
                    "model": model,
                    "success_rate": results["summary"]["success_rate"],
                    "avg_time": results["summary"]["avg_generation_time"],
                    "avg_tokens": results["summary"]["avg_tokens_used"]
                })
        
        # Sort by success rate, then by speed
        model_rankings.sort(key=lambda x: (x["success_rate"], -x["avg_time"]), reverse=True)
        
        summary["performance_ranking"] = model_rankings
        
        if model_rankings:
            summary["best_model"] = model_rankings[0]["model"]
            summary["worst_model"] = model_rankings[-1]["model"]
        
        # Generate insights
        insights = []
        if len(model_rankings) > 1:
            best = model_rankings[0]
            worst = model_rankings[-1]
            
            insights.append(f"{best['model']} achieved {best['success_rate']:.1f}% success rate vs {worst['model']} at {worst['success_rate']:.1f}%")
            
            # Find fastest model
            fastest = min(model_rankings, key=lambda x: x["avg_time"])
            insights.append(f"{fastest['model']} was fastest with {fastest['avg_time']:.2f}s average generation time")
            
            # Find most efficient model (success rate / time)
            for ranking in model_rankings:
                ranking["efficiency"] = ranking["success_rate"] / max(ranking["avg_time"], 0.1)
            
            most_efficient = max(model_rankings, key=lambda x: x["efficiency"])
            insights.append(f"{most_efficient['model']} was most efficient (success rate / time)")
        
        summary["key_insights"] = insights
        
        return summary
    
    def print_summary(self, results: Dict[str, Any]):
        """Print formatted summary of results"""
        print("\n" + "="*80)
        print("🎯 EXTENDED MODEL COMPARISON SUMMARY")
        print("="*80)
        
        if "summary" in results and results["summary"]["performance_ranking"]:
            print("\n📊 Model Performance Ranking:")
            for i, ranking in enumerate(results["summary"]["performance_ranking"], 1):
                print(f"{i}. {ranking['model']:15} - {ranking['success_rate']:5.1f}% success, {ranking['avg_time']:6.2f}s avg time")
        
        if "summary" in results and results["summary"]["key_insights"]:
            print("\n💡 Key Insights:")
            for insight in results["summary"]["key_insights"]:
                print(f"   • {insight}")
        
        print("\n" + "="*80)


async def main():
    """Run extended model comparison"""
    comparison = ExtendedModelComparison()
    
    try:
        results = await comparison.run_extended_comparison()
        comparison.print_summary(results)
        
        print(f"\n✅ Extended model comparison completed!")
        print(f"📁 Results saved to data/results/")
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 