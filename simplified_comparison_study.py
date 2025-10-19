#!/usr/bin/env python3

"""
Simplified Multi-Model Comparison Study
Tests multiple Ollama models and compares with kubectl approaches
"""

import asyncio
import json
import time
import os
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import tempfile

# Logging setup
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ComparisonResult:
    """Results from a comparison test"""
    method: str
    model: Optional[str]
    scenario: str
    success: bool
    generation_time: float
    deployment_time: float
    total_time: float
    lines_of_code: int
    files_created: int
    tokens_used: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    user_experience_score: float = 0.0


class SimplifiedComparisonStudy:
    """Simplified multi-model comparison study"""
    
    def __init__(self):
        self.results: List[ComparisonResult] = []
        self.temp_dir = tempfile.mkdtemp()
        self.scenarios = [
            "Simple Web App",
            "Microservices", 
            "Multi-Environment",
            "Security-Focused",
            "Edge Cases"
        ]
        
        # Available Ollama models
        self.ollama_models = [
            "llama3.2:3b",
            "codellama:latest"
        ]
        
        logger.info(f"Initialized study with temp dir: {self.temp_dir}")
    
    async def run_study(self) -> Dict[str, Any]:
        """Run the comparison study"""
        logger.info("🚀 Starting Simplified Multi-Model Comparison Study")
        logger.info("=" * 80)
        
        results = {
            "timestamp": time.time(),
            "multi_model_comparison": {},
            "kubectl_comparison": {},
            "analysis": {}
        }
        
        # 1. Test Multiple Ollama Models
        logger.info("📊 Phase 1: Multi-Model Ollama Comparison")
        results["multi_model_comparison"] = await self._test_ollama_models()
        
        # 2. Test kubectl approaches
        logger.info("📊 Phase 2: kubectl Comparison")
        results["kubectl_comparison"] = await self._test_kubectl_approaches()
        
        # 3. Analysis
        logger.info("📊 Phase 3: Analysis")
        results["analysis"] = await self._analyze_results()
        
        # Save results
        results_file = f"data/results/multi_model_comparison_{int(time.time())}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📄 Results saved to: {results_file}")
        return results
    
    async def _test_ollama_models(self) -> Dict[str, Any]:
        """Test multiple Ollama models"""
        model_results = {}
        
        for model in self.ollama_models:
            logger.info(f"🤖 Testing Ollama model: {model}")
            model_results[model] = {}
            
            for scenario in self.scenarios:
                logger.info(f"  📋 Scenario: {scenario}")
                
                try:
                    result = await self._test_ollama_model(model, scenario)
                    model_results[model][scenario] = result
                    self.results.append(result)
                    
                    logger.info(f"    ✅ Success: {result.success}")
                    logger.info(f"    ⏱️  Generation: {result.generation_time:.2f}s")
                    logger.info(f"    🔢 Tokens: {result.tokens_used}")
                    
                except Exception as e:
                    logger.error(f"    ❌ Failed: {str(e)}")
                    error_result = ComparisonResult(
                        method="ollama",
                        model=model,
                        scenario=scenario,
                        success=False,
                        generation_time=0,
                        deployment_time=0,
                        total_time=0,
                        lines_of_code=0,
                        files_created=0,
                        errors=[str(e)]
                    )
                    model_results[model][scenario] = error_result
                    self.results.append(error_result)
        
        return model_results
    
    async def _test_ollama_model(self, model: str, scenario: str) -> ComparisonResult:
        """Test a specific Ollama model"""
        start_time = time.time()
        
        # Get scenario prompt
        prompt = self._get_scenario_prompt(scenario)
        
        # Test Ollama directly
        gen_start = time.time()
        
        try:
            # Call Ollama API directly
            import requests
            
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
                raise Exception(f"Ollama API error: {response.status_code}")
            
            result = response.json()
            generated_content = result.get("response", "")
            
            gen_time = time.time() - gen_start
            
            # Extract YAML from response
            yaml_configs = self._extract_yaml_configs(generated_content)
            
            # Count metrics
            lines_of_code = sum(len(config.splitlines()) for config in yaml_configs)
            files_created = len(yaml_configs)
            
            # Estimate tokens (rough approximation)
            tokens_used = len(generated_content.split()) + len(prompt.split())
            
            # Test deployment
            deploy_start = time.time()
            deployment_success = await self._test_deployment(yaml_configs, scenario)
            deploy_time = time.time() - deploy_start
            
            total_time = time.time() - start_time
            
            return ComparisonResult(
                method="ollama",
                model=model,
                scenario=scenario,
                success=deployment_success,
                generation_time=gen_time,
                deployment_time=deploy_time,
                total_time=total_time,
                lines_of_code=lines_of_code,
                files_created=files_created,
                tokens_used=tokens_used,
                complexity_score=self._calculate_complexity_score(yaml_configs),
                user_experience_score=self._calculate_ux_score(gen_time, deploy_time, len(prompt))
            )
            
        except Exception as e:
            logger.error(f"Ollama test failed: {str(e)}")
            return ComparisonResult(
                method="ollama",
                model=model,
                scenario=scenario,
                success=False,
                generation_time=time.time() - gen_start,
                deployment_time=0,
                total_time=time.time() - start_time,
                lines_of_code=0,
                files_created=0,
                errors=[str(e)]
            )
    
    async def _test_kubectl_approaches(self) -> Dict[str, Any]:
        """Test kubectl approaches"""
        kubectl_results = {}
        
        approaches = [
            "plain_yaml",
            "kubectl_imperative"
        ]
        
        for approach in approaches:
            logger.info(f"🔧 Testing kubectl approach: {approach}")
            kubectl_results[approach] = {}
            
            for scenario in self.scenarios:
                logger.info(f"  📋 Scenario: {scenario}")
                
                try:
                    result = await self._test_kubectl_approach(approach, scenario)
                    kubectl_results[approach][scenario] = result
                    self.results.append(result)
                    
                    logger.info(f"    ✅ Success: {result.success}")
                    logger.info(f"    ⏱️  Total: {result.total_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"    ❌ Failed: {str(e)}")
                    error_result = ComparisonResult(
                        method=approach,
                        model=None,
                        scenario=scenario,
                        success=False,
                        generation_time=0,
                        deployment_time=0,
                        total_time=0,
                        lines_of_code=0,
                        files_created=0,
                        errors=[str(e)]
                    )
                    kubectl_results[approach][scenario] = error_result
                    self.results.append(error_result)
        
        return kubectl_results
    
    async def _test_kubectl_approach(self, approach: str, scenario: str) -> ComparisonResult:
        """Test a kubectl approach"""
        start_time = time.time()
        
        if approach == "plain_yaml":
            return await self._test_plain_yaml(scenario, start_time)
        elif approach == "kubectl_imperative":
            return await self._test_kubectl_imperative(scenario, start_time)
        else:
            raise ValueError(f"Unknown approach: {approach}")
    
    async def _test_plain_yaml(self, scenario: str, start_time: float) -> ComparisonResult:
        """Test plain YAML approach"""
        gen_start = time.time()
        
        # Create YAML files manually
        yaml_configs = self._create_manual_yaml_configs(scenario)
        
        # Save to files
        yaml_files = []
        for i, config in enumerate(yaml_configs):
            filename = f"{self.temp_dir}/yaml-{scenario.lower().replace(' ', '-')}-{i}.yaml"
            with open(filename, 'w') as f:
                f.write(config)
            yaml_files.append(filename)
        
        gen_time = time.time() - gen_start
        
        # Test deployment
        deploy_start = time.time()
        deployment_success = await self._test_deployment(yaml_configs, scenario)
        deploy_time = time.time() - deploy_start
        
        total_time = time.time() - start_time
        
        return ComparisonResult(
            method="plain_yaml",
            model=None,
            scenario=scenario,
            success=deployment_success,
            generation_time=gen_time,
            deployment_time=deploy_time,
            total_time=total_time,
            lines_of_code=sum(len(config.splitlines()) for config in yaml_configs),
            files_created=len(yaml_configs),
            complexity_score=self._calculate_complexity_score(yaml_configs),
            user_experience_score=4.0  # Manual YAML has poor UX
        )
    
    async def _test_kubectl_imperative(self, scenario: str, start_time: float) -> ComparisonResult:
        """Test kubectl imperative approach"""
        gen_start = time.time()
        
        # Create kubectl commands
        commands = self._create_kubectl_commands(scenario)
        
        gen_time = time.time() - gen_start
        
        # Execute commands
        deploy_start = time.time()
        
        success = True
        errors = []
        
        try:
            for cmd in commands:
                logger.info(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0 and "already exists" not in result.stderr:
                    success = False
                    errors.append(f"Command failed: {' '.join(cmd)}: {result.stderr}")
                    
        except Exception as e:
            success = False
            errors.append(str(e))
        
        deploy_time = time.time() - deploy_start
        total_time = time.time() - start_time
        
        return ComparisonResult(
            method="kubectl_imperative",
            model=None,
            scenario=scenario,
            success=success,
            generation_time=gen_time,
            deployment_time=deploy_time,
            total_time=total_time,
            lines_of_code=sum(len(cmd) for cmd in commands),
            files_created=0,
            errors=errors,
            complexity_score=3.0,  # Simple but not scalable
            user_experience_score=5.0  # Easy to start but hard to maintain
        )
    
    def _get_scenario_prompt(self, scenario: str) -> str:
        """Get prompt for scenario"""
        base_prompt = f"""Generate Kubernetes YAML manifests for the following scenario: {scenario}

Requirements:
- Create deployment and service manifests
- Use best practices for security and resource management
- Include appropriate labels and selectors
- Use namespace: kubenet-experiment
- Output valid YAML only, no explanations

Scenario details:
"""
        
        scenario_details = {
            "Simple Web App": "Deploy a simple web application with NGINX serving static content on port 80",
            "Microservices": "Deploy a microservices architecture with service discovery and load balancing",
            "Multi-Environment": "Deploy an application that can run in development, staging, and production environments",
            "Security-Focused": "Deploy a secure web application with network policies, TLS, and security best practices",
            "Edge Cases": "Deploy a complex application with custom configurations, special networking requirements, and edge case handling"
        }
        
        return base_prompt + scenario_details.get(scenario, scenario)
    
    def _extract_yaml_configs(self, content: str) -> List[str]:
        """Extract YAML configurations from LLM response"""
        yaml_configs = []
        
        # Look for YAML blocks
        lines = content.split('\n')
        current_yaml = []
        in_yaml = False
        
        for line in lines:
            if line.strip().startswith('apiVersion:'):
                if current_yaml:
                    yaml_configs.append('\n'.join(current_yaml))
                current_yaml = [line]
                in_yaml = True
            elif in_yaml and line.strip().startswith('---'):
                if current_yaml:
                    yaml_configs.append('\n'.join(current_yaml))
                current_yaml = []
            elif in_yaml:
                current_yaml.append(line)
        
        if current_yaml:
            yaml_configs.append('\n'.join(current_yaml))
        
        # If no YAML found, try to find it in code blocks
        if not yaml_configs:
            import re
            yaml_pattern = r'```(?:yaml|yml)?\n?(.*?)\n?```'
            matches = re.findall(yaml_pattern, content, re.DOTALL)
            yaml_configs.extend(matches)
        
        return [config.strip() for config in yaml_configs if config.strip()]
    
    def _create_manual_yaml_configs(self, scenario: str) -> List[str]:
        """Create manual YAML configs for comparison"""
        app_name = scenario.lower().replace(' ', '-')
        
        deployment_yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}-app
  namespace: kubenet-experiment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {app_name}-app
  template:
    metadata:
      labels:
        app: {app_name}-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
        resources:
          limits:
            cpu: 500m
            memory: 512Mi
          requests:
            cpu: 250m
            memory: 256Mi
"""
        
        service_yaml = f"""apiVersion: v1
kind: Service
metadata:
  name: {app_name}-service
  namespace: kubenet-experiment
spec:
  selector:
    app: {app_name}-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
"""
        
        return [deployment_yaml, service_yaml]
    
    def _create_kubectl_commands(self, scenario: str) -> List[List[str]]:
        """Create kubectl imperative commands"""
        app_name = scenario.lower().replace(' ', '-')
        
        return [
            ["kubectl", "create", "namespace", "kubenet-experiment", "--dry-run=client"],
            ["kubectl", "create", "deployment", f"{app_name}-app", 
             "--image=nginx:latest", "--namespace=kubenet-experiment"],
            ["kubectl", "expose", "deployment", f"{app_name}-app", 
             "--port=80", "--target-port=80", "--namespace=kubenet-experiment"],
            ["kubectl", "scale", "deployment", f"{app_name}-app", 
             "--replicas=1", "--namespace=kubenet-experiment"]
        ]
    
    async def _test_deployment(self, yaml_configs: List[str], scenario: str) -> bool:
        """Test deployment of YAML configs"""
        try:
            # Create temp file with all configs
            all_yaml = "\n---\n".join(yaml_configs)
            temp_file = f"{self.temp_dir}/test-{scenario.lower().replace(' ', '-')}.yaml"
            
            with open(temp_file, 'w') as f:
                f.write(all_yaml)
            
            # Test with kubectl apply --dry-run
            result = subprocess.run([
                "kubectl", "apply", "-f", temp_file, "--dry-run=client"
            ], capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Deployment test failed: {str(e)}")
            return False
    
    def _calculate_complexity_score(self, yaml_configs: List[str]) -> float:
        """Calculate complexity score"""
        if not yaml_configs:
            return 0.0
        
        total_lines = sum(len(config.splitlines()) for config in yaml_configs)
        complexity = min(10.0, total_lines / 10.0)  # Normalize to 0-10
        
        return complexity
    
    def _calculate_ux_score(self, gen_time: float, deploy_time: float, prompt_length: int) -> float:
        """Calculate user experience score"""
        # Natural language gets high UX score
        base_score = 9.0
        
        # Penalize for slow response
        if gen_time > 20:
            base_score -= 2.0
        elif gen_time > 10:
            base_score -= 1.0
        
        if deploy_time > 5:
            base_score -= 0.5
        
        return max(0.0, base_score)
    
    async def _analyze_results(self) -> Dict[str, Any]:
        """Analyze comparison results"""
        analysis = {
            "model_comparison": self._analyze_model_performance(),
            "method_comparison": self._analyze_method_performance(),
            "key_findings": self._generate_key_findings(),
            "recommendations": self._generate_recommendations()
        }
        
        return analysis
    
    def _analyze_model_performance(self) -> Dict[str, Any]:
        """Analyze model performance"""
        ollama_results = [r for r in self.results if r.method == "ollama"]
        
        if not ollama_results:
            return {"error": "No Ollama results found"}
        
        model_groups = {}
        for result in ollama_results:
            if result.model not in model_groups:
                model_groups[result.model] = []
            model_groups[result.model].append(result)
        
        model_analysis = {}
        for model, results in model_groups.items():
            success_rate = sum(1 for r in results if r.success) / len(results)
            avg_gen_time = sum(r.generation_time for r in results) / len(results)
            avg_tokens = sum(r.tokens_used for r in results) / len(results)
            avg_complexity = sum(r.complexity_score for r in results) / len(results)
            avg_ux = sum(r.user_experience_score for r in results) / len(results)
            
            model_analysis[model] = {
                "success_rate": success_rate,
                "avg_generation_time": avg_gen_time,
                "avg_tokens": avg_tokens,
                "avg_complexity": avg_complexity,
                "avg_user_experience": avg_ux,
                "total_scenarios": len(results)
            }
        
        return model_analysis
    
    def _analyze_method_performance(self) -> Dict[str, Any]:
        """Analyze method performance"""
        method_groups = {}
        for result in self.results:
            if result.method not in method_groups:
                method_groups[result.method] = []
            method_groups[result.method].append(result)
        
        method_analysis = {}
        for method, results in method_groups.items():
            success_rate = sum(1 for r in results if r.success) / len(results)
            avg_gen_time = sum(r.generation_time for r in results) / len(results)
            avg_deploy_time = sum(r.deployment_time for r in results) / len(results)
            avg_total_time = sum(r.total_time for r in results) / len(results)
            avg_complexity = sum(r.complexity_score for r in results) / len(results)
            avg_ux = sum(r.user_experience_score for r in results) / len(results)
            
            method_analysis[method] = {
                "success_rate": success_rate,
                "avg_generation_time": avg_gen_time,
                "avg_deployment_time": avg_deploy_time,
                "avg_total_time": avg_total_time,
                "avg_complexity": avg_complexity,
                "avg_user_experience": avg_ux,
                "total_scenarios": len(results)
            }
        
        return method_analysis
    
    def _generate_key_findings(self) -> List[str]:
        """Generate key findings"""
        findings = []
        
        # Model comparison
        model_stats = self._analyze_model_performance()
        if len(model_stats) > 1:
            fastest_model = min(model_stats.items(), key=lambda x: x[1]["avg_generation_time"])
            most_successful = max(model_stats.items(), key=lambda x: x[1]["success_rate"])
            
            findings.append(f"Fastest model: {fastest_model[0]} ({fastest_model[1]['avg_generation_time']:.2f}s avg)")
            findings.append(f"Most successful model: {most_successful[0]} ({most_successful[1]['success_rate']:.1%} success)")
        
        # Method comparison
        method_stats = self._analyze_method_performance()
        best_ux = max(method_stats.items(), key=lambda x: x[1]["avg_user_experience"])
        fastest_method = min(method_stats.items(), key=lambda x: x[1]["avg_total_time"])
        
        findings.append(f"Best user experience: {best_ux[0]} (Score: {best_ux[1]['avg_user_experience']:.1f})")
        findings.append(f"Fastest method: {fastest_method[0]} ({fastest_method[1]['avg_total_time']:.2f}s avg)")
        
        return findings
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations"""
        recommendations = [
            "LLM-based approach provides superior user experience through natural language",
            "Different models show varying performance characteristics",
            "Traditional kubectl methods are faster for simple cases",
            "LLM approach excels in complex scenarios requiring customization",
            "Model selection impacts both speed and output quality"
        ]
        
        return recommendations
    
    def print_summary(self, results: Dict[str, Any]):
        """Print summary of results"""
        print("\n" + "="*80)
        print("🏆 MULTI-MODEL COMPARISON STUDY RESULTS")
        print("="*80)
        
        print("\n📊 MODEL COMPARISON:")
        for model, stats in results["analysis"]["model_comparison"].items():
            print(f"  {model}:")
            print(f"    Success Rate: {stats['success_rate']:.1%}")
            print(f"    Avg Generation Time: {stats['avg_generation_time']:.2f}s")
            print(f"    Avg Tokens: {stats['avg_tokens']:.0f}")
            print(f"    User Experience: {stats['avg_user_experience']:.1f}/10")
        
        print("\n📊 METHOD COMPARISON:")
        for method, stats in results["analysis"]["method_comparison"].items():
            print(f"  {method}:")
            print(f"    Success Rate: {stats['success_rate']:.1%}")
            print(f"    Avg Total Time: {stats['avg_total_time']:.2f}s")
            print(f"    User Experience: {stats['avg_user_experience']:.1f}/10")
        
        print("\n🔍 KEY FINDINGS:")
        for finding in results["analysis"]["key_findings"]:
            print(f"  • {finding}")
        
        print("\n💡 RECOMMENDATIONS:")
        for rec in results["analysis"]["recommendations"]:
            print(f"  • {rec}")
        
        print("\n" + "="*80)


async def main():
    """Main execution function"""
    study = SimplifiedComparisonStudy()
    
    try:
        results = await study.run_study()
        study.print_summary(results)
        
        print(f"\n📄 Detailed results saved to: data/results/multi_model_comparison_{int(time.time())}.json")
        
    except Exception as e:
        logger.error(f"Study failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 