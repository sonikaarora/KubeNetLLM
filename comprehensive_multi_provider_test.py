#!/usr/bin/env python3
"""
Comprehensive Multi-Provider Model Comparison
Tests Ollama models + Groq + other providers for complete evaluation
"""

import asyncio
import json
import time
import yaml
import os
import requests
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import structlog

# Configure logging
structlog.configure(
    processors=[structlog.dev.ConsoleRenderer(colors=True)],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@dataclass
class ModelTestResult:
    """Result from testing a specific model"""
    model: str
    provider: str
    scenario: str
    success: bool
    generation_time: float
    tokens_used: int
    yaml_quality: str
    generated_content: str
    error: Optional[str] = None


class ComprehensiveModelComparison:
    """Test multiple models across different providers"""
    
    def __init__(self):
        self.test_scenario = "Simple Web App"
        
        # Models to test per provider
        self.provider_models = {
            "ollama": [
                "llama3.2:3b",
                "codellama:latest", 
                "llama3.1:8b",
                "mistral:7b",
                "phi3:mini"
            ],
            "groq": [
                "llama3-8b-8192",
                "llama3-70b-8192", 
                "mixtral-8x7b-32768",
                "gemma-7b-it"
            ]
        }
        
        # Groq API key (set as environment variable)
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        
    def get_optimized_prompt(self) -> str:
        """Get the optimized prompt that works well for CodeLlama"""
        return """
You must generate ONLY valid Kubernetes YAML configuration. Do not include any explanations, comments, or code blocks.

Requirements:
- A Deployment resource with nginx container
- A Service resource to expose the application  
- Use port 80
- Set replicas to 2
- Include proper labels and selectors

Output format: Start directly with "apiVersion:" and provide only the YAML content.
"""
    
    async def test_ollama_model(self, model: str) -> ModelTestResult:
        """Test an Ollama model"""
        logger.info(f"🤖 Testing Ollama model: {model}")
        start_time = time.time()
        
        try:
            prompt = self.get_optimized_prompt()
            
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
                    provider="ollama",
                    scenario=self.test_scenario,
                    success=False,
                    generation_time=time.time() - start_time,
                    tokens_used=0,
                    yaml_quality="API Error",
                    generated_content="",
                    error=f"Ollama API error: {response.status_code}"
                )
            
            result = response.json()
            generated_content = result.get("response", "")
            generation_time = time.time() - start_time
            
            # Analyze YAML quality
            success, quality = self.analyze_yaml_quality(generated_content)
            tokens_used = len(generated_content.split()) + len(prompt.split())
            
            return ModelTestResult(
                model=model,
                provider="ollama",
                scenario=self.test_scenario,
                success=success,
                generation_time=generation_time,
                tokens_used=tokens_used,
                yaml_quality=quality,
                generated_content=generated_content[:300] + "..." if len(generated_content) > 300 else generated_content
            )
            
        except Exception as e:
            return ModelTestResult(
                model=model,
                provider="ollama",
                scenario=self.test_scenario,
                success=False,
                generation_time=time.time() - start_time,
                tokens_used=0,
                yaml_quality="Error",
                generated_content="",
                error=str(e)
            )
    
    async def test_groq_model(self, model: str) -> ModelTestResult:
        """Test a Groq model"""
        logger.info(f"☁️ Testing Groq model: {model}")
        start_time = time.time()
        
        if not self.groq_api_key:
            return ModelTestResult(
                model=model,
                provider="groq",
                scenario=self.test_scenario,
                success=False,
                generation_time=0,
                tokens_used=0,
                yaml_quality="No API Key",
                generated_content="",
                error="GROQ_API_KEY environment variable not set"
            )
        
        try:
            prompt = self.get_optimized_prompt()
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4096
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        generated_content = result["choices"][0]["message"]["content"]
                        tokens_used = result.get("usage", {}).get("total_tokens", 0)
                        generation_time = time.time() - start_time
                        
                        # Analyze YAML quality
                        success, quality = self.analyze_yaml_quality(generated_content)
                        
                        return ModelTestResult(
                            model=model,
                            provider="groq",
                            scenario=self.test_scenario,
                            success=success,
                            generation_time=generation_time,
                            tokens_used=tokens_used,
                            yaml_quality=quality,
                            generated_content=generated_content[:300] + "..." if len(generated_content) > 300 else generated_content
                        )
                    else:
                        error_text = await response.text()
                        return ModelTestResult(
                            model=model,
                            provider="groq",
                            scenario=self.test_scenario,
                            success=False,
                            generation_time=time.time() - start_time,
                            tokens_used=0,
                            yaml_quality="API Error",
                            generated_content="",
                            error=f"Groq API error {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            return ModelTestResult(
                model=model,
                provider="groq",
                scenario=self.test_scenario,
                success=False,
                generation_time=time.time() - start_time,
                tokens_used=0,
                yaml_quality="Error",
                generated_content="",
                error=str(e)
            )
    
    def analyze_yaml_quality(self, content: str) -> tuple[bool, str]:
        """Analyze YAML quality with detailed feedback"""
        try:
            # Clean the content
            cleaned_content = self.extract_yaml_from_content(content)
            
            if not cleaned_content:
                return False, "No YAML content found"
            
            # Try to parse as YAML
            try:
                yaml_docs = list(yaml.safe_load_all(cleaned_content))
                
                if not yaml_docs:
                    return False, "No valid YAML documents"
                
                # Check for Kubernetes-specific fields
                k8s_valid = True
                k8s_issues = []
                
                for doc in yaml_docs:
                    if not isinstance(doc, dict):
                        continue
                    
                    # Check required fields
                    if 'apiVersion' not in doc:
                        k8s_issues.append("Missing apiVersion")
                        k8s_valid = False
                    
                    if 'kind' not in doc:
                        k8s_issues.append("Missing kind")
                        k8s_valid = False
                    
                    if 'metadata' not in doc:
                        k8s_issues.append("Missing metadata")
                        k8s_valid = False
                
                if k8s_valid and len(yaml_docs) >= 2:
                    return True, "Valid Kubernetes YAML"
                elif k8s_valid:
                    return True, "Valid YAML but incomplete"
                else:
                    return False, f"Invalid Kubernetes format: {', '.join(k8s_issues)}"
                    
            except yaml.YAMLError as e:
                return False, f"YAML syntax error: {str(e)}"
            
        except Exception as e:
            return False, f"Analysis error: {str(e)}"
    
    def extract_yaml_from_content(self, content: str) -> str:
        """Extract YAML content from response"""
        lines = content.split('\n')
        yaml_lines = []
        in_yaml_block = False
        
        for line in lines:
            # Check for code block markers
            if line.strip().startswith('```'):
                in_yaml_block = not in_yaml_block
                continue
            
            # If we're in a YAML block or find apiVersion, start collecting
            if in_yaml_block or line.strip().startswith('apiVersion:'):
                yaml_lines.append(line)
                in_yaml_block = True
            elif yaml_lines and line.strip() == '':
                yaml_lines.append(line)  # Keep blank lines in YAML
            elif yaml_lines and not line.strip().startswith('#'):
                yaml_lines.append(line)  # Continue collecting YAML
        
        return '\n'.join(yaml_lines).strip()
    
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_ollama_models(self) -> List[str]:
        """Get available Ollama models"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data["models"]]
        except:
            pass
        return []
    
    async def run_comprehensive_comparison(self) -> Dict[str, Any]:
        """Run comprehensive multi-provider comparison"""
        logger.info("🚀 Starting Comprehensive Multi-Provider Model Comparison")
        logger.info("=" * 80)
        
        results = {
            "timestamp": time.time(),
            "scenario": self.test_scenario,
            "providers_tested": [],
            "models_results": {},
            "summary": {},
            "provider_performance": {}
        }
        
        # Test Ollama models
        if self.check_ollama_available():
            logger.info("🔧 Testing Ollama models...")
            available_ollama = self.get_ollama_models()
            logger.info(f"Available Ollama models: {available_ollama}")
            
            results["providers_tested"].append("ollama")
            results["models_results"]["ollama"] = {}
            
            ollama_success_count = 0
            ollama_total_time = 0
            ollama_total_tokens = 0
            
            for model in self.provider_models["ollama"]:
                if model in available_ollama:
                    test_result = await self.test_ollama_model(model)
                    
                    results["models_results"]["ollama"][model] = {
                        "success": test_result.success,
                        "generation_time": test_result.generation_time,
                        "tokens_used": test_result.tokens_used,
                        "yaml_quality": test_result.yaml_quality,
                        "error": test_result.error
                    }
                    
                    if test_result.success:
                        ollama_success_count += 1
                    
                    ollama_total_time += test_result.generation_time
                    ollama_total_tokens += test_result.tokens_used
                    
                    logger.info(f"   {model}: {'✅' if test_result.success else '❌'} {test_result.yaml_quality}")
                else:
                    logger.warning(f"   {model}: ⚠️ Not installed")
            
            # Ollama summary
            if self.provider_models["ollama"]:
                tested_count = len([m for m in self.provider_models["ollama"] if m in available_ollama])
                if tested_count > 0:
                    results["provider_performance"]["ollama"] = {
                        "success_rate": (ollama_success_count / tested_count) * 100,
                        "avg_generation_time": ollama_total_time / tested_count,
                        "avg_tokens": ollama_total_tokens / tested_count,
                        "models_tested": tested_count
                    }
        else:
            logger.warning("⚠️ Ollama not available")
        
        # Test Groq models
        logger.info("☁️ Testing Groq models...")
        if self.groq_api_key:
            logger.info(f"Groq API key available: {self.groq_api_key[:8]}...")
            
            results["providers_tested"].append("groq")
            results["models_results"]["groq"] = {}
            
            groq_success_count = 0
            groq_total_time = 0
            groq_total_tokens = 0
            
            for model in self.provider_models["groq"]:
                test_result = await self.test_groq_model(model)
                
                results["models_results"]["groq"][model] = {
                    "success": test_result.success,
                    "generation_time": test_result.generation_time,
                    "tokens_used": test_result.tokens_used,
                    "yaml_quality": test_result.yaml_quality,
                    "error": test_result.error
                }
                
                if test_result.success:
                    groq_success_count += 1
                
                groq_total_time += test_result.generation_time
                groq_total_tokens += test_result.tokens_used
                
                logger.info(f"   {model}: {'✅' if test_result.success else '❌'} {test_result.yaml_quality}")
            
            # Groq summary
            if self.provider_models["groq"]:
                results["provider_performance"]["groq"] = {
                    "success_rate": (groq_success_count / len(self.provider_models["groq"])) * 100,
                    "avg_generation_time": groq_total_time / len(self.provider_models["groq"]),
                    "avg_tokens": groq_total_tokens / len(self.provider_models["groq"]),
                    "models_tested": len(self.provider_models["groq"])
                }
        else:
            logger.warning("⚠️ Groq API key not available (set GROQ_API_KEY environment variable)")
            logger.info("💡 To test Groq models:")
            logger.info("   export GROQ_API_KEY='your_api_key_here'")
            logger.info("   Get a free API key at: https://console.groq.com/")
        
        # Generate overall summary
        results["summary"] = self.generate_comparison_summary(results)
        
        # Save results
        os.makedirs("data/results", exist_ok=True)
        results_file = f"data/results/comprehensive_multi_provider_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📄 Results saved to: {results_file}")
        
        return results
    
    def generate_comparison_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive comparison summary"""
        summary = {
            "best_provider": None,
            "best_model": None,
            "provider_rankings": [],
            "model_rankings": [],
            "key_insights": []
        }
        
        # Rank providers
        provider_rankings = []
        for provider, perf in results.get("provider_performance", {}).items():
            provider_rankings.append({
                "provider": provider,
                "success_rate": perf["success_rate"],
                "avg_time": perf["avg_generation_time"],
                "avg_tokens": perf["avg_tokens"],
                "models_tested": perf["models_tested"]
            })
        
        # Sort by success rate, then by speed
        provider_rankings.sort(key=lambda x: (x["success_rate"], -x["avg_time"]), reverse=True)
        summary["provider_rankings"] = provider_rankings
        
        if provider_rankings:
            summary["best_provider"] = provider_rankings[0]["provider"]
        
        # Rank individual models
        model_rankings = []
        for provider, models in results.get("models_results", {}).items():
            for model, result in models.items():
                if isinstance(result, dict) and "success" in result:
                    model_rankings.append({
                        "model": model,
                        "provider": provider,
                        "success": result["success"],
                        "generation_time": result.get("generation_time", 0),
                        "tokens": result.get("tokens_used", 0),
                        "quality": result.get("yaml_quality", "Unknown")
                    })
        
        # Sort models by success, then by speed
        model_rankings.sort(key=lambda x: (x["success"], -x["generation_time"]), reverse=True)
        summary["model_rankings"] = model_rankings[:10]  # Top 10
        
        if model_rankings:
            summary["best_model"] = f"{model_rankings[0]['model']} ({model_rankings[0]['provider']})"
        
        # Generate insights
        insights = []
        if len(provider_rankings) > 1:
            best_provider = provider_rankings[0]
            insights.append(f"{best_provider['provider']} performed best with {best_provider['success_rate']:.1f}% success rate")
        
        successful_models = [m for m in model_rankings if m["success"]]
        if successful_models:
            insights.append(f"{len(successful_models)} models achieved successful YAML generation")
        
        # Speed comparison
        if len(provider_rankings) > 1:
            fastest_provider = min(provider_rankings, key=lambda x: x["avg_time"])
            insights.append(f"{fastest_provider['provider']} was fastest with {fastest_provider['avg_time']:.2f}s average")
        
        summary["key_insights"] = insights
        
        return summary
    
    def print_summary(self, results: Dict[str, Any]):
        """Print formatted summary of results"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE MULTI-PROVIDER COMPARISON SUMMARY")
        print("="*80)
        
        summary = results.get("summary", {})
        
        # Provider performance
        if "provider_rankings" in summary and summary["provider_rankings"]:
            print("\n📊 Provider Performance Ranking:")
            for i, provider in enumerate(summary["provider_rankings"], 1):
                print(f"{i}. {provider['provider']:10} - {provider['success_rate']:5.1f}% success, {provider['avg_time']:6.2f}s avg time, {provider['models_tested']} models")
        
        # Top models
        if "model_rankings" in summary and summary["model_rankings"]:
            print("\n🏆 Top Performing Models:")
            for i, model in enumerate(summary["model_rankings"][:5], 1):
                status = "✅" if model["success"] else "❌"
                print(f"{i}. {model['model']:20} ({model['provider']:8}) - {status} {model['quality']}")
        
        # Key insights
        if "key_insights" in summary and summary["key_insights"]:
            print("\n💡 Key Insights:")
            for insight in summary["key_insights"]:
                print(f"   • {insight}")
        
        # Setup instructions
        print("\n🔧 Setup Notes:")
        if not results.get("models_results", {}).get("groq"):
            print("   • To test Groq: export GROQ_API_KEY='your_key' (get free key at console.groq.com)")
        
        print("\n" + "="*80)


async def main():
    """Run comprehensive multi-provider comparison"""
    comparison = ComprehensiveModelComparison()
    
    try:
        results = await comparison.run_comprehensive_comparison()
        comparison.print_summary(results)
        
        print(f"\n✅ Comprehensive multi-provider comparison completed!")
        print(f"📁 Results saved to data/results/")
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 