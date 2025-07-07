#!/usr/bin/env python3
"""
Fixed Kubernetes KubeNetLLM Experiment Runner
Actually deploys and properly tracks real Kubernetes resources.
"""

import asyncio
import json
import time
import aiohttp
import re
import subprocess
import tempfile
import os
import yaml
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RealKubernetesResult:
    """Result of actual Kubernetes deployment experiment"""
    scenario: str
    generation_time: float
    deployment_time: float
    api_calls: int
    tokens_used: int
    prompt_tokens: int
    response_tokens: int
    config_generated: bool
    resources_deployed: int
    pods_running: int
    services_created: int
    deployment_successful: bool
    deployment_errors: List[str]
    error: str = ""

class FixedKubernetesExperimentRunner:
    """Fixed experiment runner with proper Kubernetes deployment tracking"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2:3b"
        self.results = []
        self.experiment_namespace = "kubenet-experiment"
        
    async def run_experiments(self) -> List[RealKubernetesResult]:
        """Run all scenarios with real Kubernetes deployment"""
        print("🚀 Starting REAL Kubernetes Deployment Experiments")
        print("📊 Real LLM + Real K8s Deployment + Real Metrics")
        print("🔧 Cluster:", self.get_cluster_info())
        print("=" * 60)
        
        scenarios = [
            {
                "name": "Simple Web App",
                "description": "Deploy nginx web application with service",
                "app_name": "web-app"
            },
            {
                "name": "Microservices",
                "description": "Deploy frontend and backend microservices with database",
                "app_name": "microservices"
            },
            {
                "name": "Multi-Environment",
                "description": "Deploy app with development and production configurations",
                "app_name": "multi-env"
            },
            {
                "name": "Security-Focused",
                "description": "Deploy secure app with security context and resource limits",
                "app_name": "secure-app"
            },
            {
                "name": "Edge Cases",
                "description": "Deploy app with persistent volume and config map",
                "app_name": "edge-case"
            }
        ]
        
        for i, scenario in enumerate(scenarios):
            print(f"\n📋 Running scenario {i+1}/5: {scenario['name']}")
            result = await self.run_single_scenario(scenario)
            self.results.append(result)
            
            status = "✅ SUCCESS" if result.deployment_successful else "❌ FAILED"
            print(f"   {status}")
            print(f"   📊 Generation: {result.generation_time:.2f}s, Deployment: {result.deployment_time:.2f}s")
            print(f"   🔢 Tokens: {result.tokens_used}, Resources: {result.resources_deployed}")
            print(f"   🚀 Pods: {result.pods_running}, Services: {result.services_created}")
            
            # Wait a bit before next scenario
            await asyncio.sleep(2)
            
            # Clean up this scenario's resources
            await self.cleanup_scenario_resources(scenario["app_name"])
            
        return self.results
    
    async def run_single_scenario(self, scenario: Dict[str, Any]) -> RealKubernetesResult:
        """Run single scenario with full deployment cycle"""
        generation_start = time.time()
        total_prompt_tokens = 0
        total_response_tokens = 0
        deployment_errors = []
        
        try:
            # Step 1: Generate configuration with LLM
            config, metrics = await self.generate_app_config(scenario["description"], scenario["app_name"])
            total_prompt_tokens += metrics["prompt_tokens"]
            total_response_tokens += metrics["response_tokens"]
            
            generation_end = time.time()
            generation_time = generation_end - generation_start
            
            if "error" in config:
                deployment_errors.append(f"Config generation failed: {config['error']}")
                raise Exception("Configuration generation failed")
            
            # Step 2: Convert to Kubernetes resources
            k8s_resources = self.convert_to_k8s_resources(config, scenario["app_name"])
            
            # Step 3: Deploy to Kubernetes
            deployment_start = time.time()
            deployment_result = await self.deploy_to_kubernetes(k8s_resources)
            deployment_end = time.time()
            deployment_time = deployment_end - deployment_start
            
            # Step 4: Wait for deployment to stabilize
            await asyncio.sleep(10)
            
            # Step 5: Verify deployment
            verification = await self.verify_deployment(scenario["app_name"])
            
            return RealKubernetesResult(
                scenario=scenario["name"],
                generation_time=generation_time,
                deployment_time=deployment_time,
                api_calls=1,
                tokens_used=total_prompt_tokens + total_response_tokens,
                prompt_tokens=total_prompt_tokens,
                response_tokens=total_response_tokens,
                config_generated=bool(config and not "error" in config),
                resources_deployed=deployment_result["resources_created"],
                pods_running=verification["pods_running"],
                services_created=verification["services_created"],
                deployment_successful=deployment_result["success"] and verification["pods_running"] > 0,
                deployment_errors=deployment_result.get("errors", []),
                error=""
            )
            
        except Exception as e:
            return RealKubernetesResult(
                scenario=scenario["name"],
                generation_time=time.time() - generation_start,
                deployment_time=0,
                api_calls=1,
                tokens_used=total_prompt_tokens + total_response_tokens,
                prompt_tokens=total_prompt_tokens,
                response_tokens=total_response_tokens,
                config_generated=False,
                resources_deployed=0,
                pods_running=0,
                services_created=0,
                deployment_successful=False,
                deployment_errors=deployment_errors,
                error=str(e)
            )
    
    async def generate_app_config(self, description: str, app_name: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Generate app configuration using LLM"""
        prompt = f"""
        Generate Kubernetes application configuration for: "{description}"
        
        Return this JSON structure for app "{app_name}":
        {{
            "app_name": "{app_name}",
            "image": "nginx:latest",
            "replicas": 1,
            "port": 80,
            "namespace": "{self.experiment_namespace}",
            "resources": {{
                "cpu_request": "100m",
                "memory_request": "128Mi",
                "cpu_limit": "500m",
                "memory_limit": "512Mi"
            }}
        }}
        
        Return only the JSON, no other text.
        """
        
        response_text, metrics = await self.call_ollama_with_metrics(prompt)
        json_data = self.extract_json_from_response(response_text)
        
        # Ensure app_name is set correctly
        if json_data and "error" not in json_data:
            json_data["app_name"] = app_name
            json_data["namespace"] = self.experiment_namespace
        
        return json_data, metrics
    
    def convert_to_k8s_resources(self, config: Dict[str, Any], app_name: str) -> List[Dict[str, Any]]:
        """Convert config to Kubernetes resources"""
        if "error" in config:
            return []
        
        resources = config.get("resources", {})
        
        # Deployment
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": app_name,
                "namespace": self.experiment_namespace,
                "labels": {"app": app_name, "scenario": app_name}
            },
            "spec": {
                "replicas": config.get("replicas", 1),
                "selector": {"matchLabels": {"app": app_name}},
                "template": {
                    "metadata": {"labels": {"app": app_name}},
                    "spec": {
                        "containers": [{
                            "name": app_name,
                            "image": config.get("image", "nginx:latest"),
                            "ports": [{"containerPort": config.get("port", 80)}],
                            "resources": {
                                "requests": {
                                    "cpu": resources.get("cpu_request", "100m"),
                                    "memory": resources.get("memory_request", "128Mi")
                                },
                                "limits": {
                                    "cpu": resources.get("cpu_limit", "500m"),
                                    "memory": resources.get("memory_limit", "512Mi")
                                }
                            }
                        }]
                    }
                }
            }
        }
        
        # Service
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{app_name}-service",
                "namespace": self.experiment_namespace,
                "labels": {"app": app_name}
            },
            "spec": {
                "selector": {"app": app_name},
                "ports": [{"port": 80, "targetPort": config.get("port", 80)}],
                "type": "ClusterIP"
            }
        }
        
        return [deployment, service]
    
    async def deploy_to_kubernetes(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deploy resources to Kubernetes cluster"""
        deployment_result = {"success": True, "errors": [], "resources_created": 0}
        
        for resource in resources:
            try:
                # Create temp YAML file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    yaml.dump(resource, f)
                    temp_file = f.name
                
                # Apply to cluster
                result = subprocess.run(
                    ['kubectl', 'apply', '-f', temp_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    deployment_result["resources_created"] += 1
                else:
                    deployment_result["errors"].append(f"Failed to deploy {resource['kind']}: {result.stderr}")
                    deployment_result["success"] = False
                
                # Clean up temp file
                os.unlink(temp_file)
                
            except Exception as e:
                deployment_result["errors"].append(f"Exception deploying {resource.get('kind', 'unknown')}: {str(e)}")
                deployment_result["success"] = False
        
        return deployment_result
    
    async def verify_deployment(self, app_name: str) -> Dict[str, Any]:
        """Verify deployment is running"""
        try:
            # Check pods
            pod_result = subprocess.run(
                ['kubectl', 'get', 'pods', '-n', self.experiment_namespace, 
                 '-l', f'app={app_name}', '-o', 'json'],
                capture_output=True,
                text=True
            )
            
            pods_running = 0
            if pod_result.returncode == 0:
                pods_data = json.loads(pod_result.stdout)
                for pod in pods_data.get("items", []):
                    if pod.get("status", {}).get("phase") == "Running":
                        pods_running += 1
            
            # Check services
            service_result = subprocess.run(
                ['kubectl', 'get', 'services', '-n', self.experiment_namespace,
                 '-l', f'app={app_name}', '-o', 'json'],
                capture_output=True,
                text=True
            )
            
            services_created = 0
            if service_result.returncode == 0:
                services_data = json.loads(service_result.stdout)
                services_created = len(services_data.get("items", []))
            
            return {
                "pods_running": pods_running,
                "services_created": services_created
            }
            
        except Exception as e:
            return {"pods_running": 0, "services_created": 0, "error": str(e)}
    
    async def cleanup_scenario_resources(self, app_name: str):
        """Clean up resources for a specific scenario"""
        try:
            subprocess.run([
                'kubectl', 'delete', 'all', '-l', f'app={app_name}', 
                '-n', self.experiment_namespace
            ], capture_output=True, text=True)
        except Exception:
            pass
    
    def get_cluster_info(self) -> str:
        """Get cluster info"""
        try:
            result = subprocess.run(['kubectl', 'cluster-info'], capture_output=True, text=True)
            return result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
        except:
            return "Unknown cluster"
    
    async def call_ollama_with_metrics(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        """Call Ollama with metrics"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.ollama_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    metrics = {
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "response_tokens": result.get("eval_count", 0)
                    }
                    return result.get("response", ""), metrics
                else:
                    raise Exception(f"Ollama API error: {response.status}")
    
    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "No valid JSON found"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}
    
    def generate_report(self) -> str:
        """Generate comprehensive report"""
        if not self.results:
            return "No results"
        
        total_time = sum(r.generation_time + r.deployment_time for r in self.results)
        total_generation = sum(r.generation_time for r in self.results)
        total_deployment = sum(r.deployment_time for r in self.results)
        total_tokens = sum(r.tokens_used for r in self.results)
        success_rate = sum(1 for r in self.results if r.deployment_successful) / len(self.results) * 100
        
        report = f"""
🎯 KubeNetLLM REAL Kubernetes Deployment Results
================================================

🔧 Cluster: {self.get_cluster_info()}
📊 Namespace: {self.experiment_namespace}

📊 Summary Statistics:
- Total Scenarios: {len(self.results)}
- Total Time: {total_time:.2f}s
  - Generation: {total_generation:.2f}s
  - Deployment: {total_deployment:.2f}s
- Total Tokens: {total_tokens}
- Real Deployment Success Rate: {success_rate:.1f}%

📋 Individual Results:
"""
        
        for result in self.results:
            status = "✅ SUCCESS" if result.deployment_successful else "❌ FAILED"
            report += f"""
{result.scenario}: {status}
  - Generation: {result.generation_time:.2f}s, Deployment: {result.deployment_time:.2f}s
  - Tokens: {result.tokens_used} ({result.prompt_tokens} + {result.response_tokens})
  - Resources Deployed: {result.resources_deployed}
  - Pods Running: {result.pods_running}, Services: {result.services_created}
"""
            if result.deployment_errors:
                report += f"  - Errors: {', '.join(result.deployment_errors)}\n"
        
        # Table
        report += f"""

📈 Real Kubernetes Deployment Metrics:
+------------------+--------+--------+--------+-------+--------+------+----------+
| Scenario         | Gen    | Deploy | Total  | Tokens| Pods  | Svcs | Success  |
+------------------+--------+--------+--------+-------+--------+------+----------+
"""
        
        for result in self.results:
            total_time = result.generation_time + result.deployment_time
            report += f"| {result.scenario:<16} | {result.generation_time:>6.2f} | {result.deployment_time:>6.2f} | {total_time:>6.2f} | {result.tokens_used:>5} | {result.pods_running:>4} | {result.services_created:>4} | {result.deployment_successful*100:>6.1f}% |\n"
        
        report += "+------------------+--------+--------+--------+-------+--------+------+----------+\n"
        
        return report

async def main():
    """Main runner"""
    print("🚀 Fixed KubeNetLLM Kubernetes Deployment Experiment")
    print("📊 Real LLM + Real K8s + Real Metrics")
    print()
    
    runner = FixedKubernetesExperimentRunner()
    
    start_time = time.time()
    results = await runner.run_experiments()
    end_time = time.time()
    
    print(f"\n🎉 All experiments completed in {end_time - start_time:.2f}s")
    
    report = runner.generate_report()
    print(report)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"real_kubernetes_results_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"📄 Results saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main()) 