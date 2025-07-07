#!/usr/bin/env python3
"""
Debug script to see what configurations are being generated
"""

import asyncio
import json
import aiohttp
import re
import yaml
import tempfile
import subprocess
import os

async def test_single_deployment():
    """Test a single deployment to debug the process"""
    print("🔍 Debugging Kubernetes Deployment Process")
    print("=" * 50)
    
    # Step 1: Generate a simple configuration
    print("\n📝 Step 1: Generate configuration with LLM")
    config = await generate_simple_config()
    print(f"Generated config: {json.dumps(config, indent=2)}")
    
    # Step 2: Convert to valid Kubernetes YAML
    print("\n🔧 Step 2: Convert to Kubernetes YAML")
    k8s_resources = convert_to_k8s_yaml(config)
    print(f"K8s resources: {len(k8s_resources)} items")
    
    # Step 3: Deploy to cluster
    print("\n🚀 Step 3: Deploy to cluster")
    result = await deploy_resources(k8s_resources)
    print(f"Deployment result: {result}")
    
    # Step 4: Check deployment status
    print("\n✅ Step 4: Check deployment status")
    await check_deployment_status()

async def generate_simple_config():
    """Generate a simple configuration using LLM"""
    prompt = """
    Generate a simple Kubernetes deployment configuration for a nginx web server.
    
    Return this exact JSON structure:
    {
        "app_name": "nginx-app",
        "image": "nginx:latest",
        "replicas": 1,
        "port": 80,
        "namespace": "kubenet-experiment"
    }
    """
    
    response = await call_ollama(prompt)
    return extract_json_from_response(response)

def convert_to_k8s_yaml(config):
    """Convert simple config to proper Kubernetes YAML"""
    if "error" in config:
        return []
    
    app_name = config.get("app_name", "test-app")
    image = config.get("image", "nginx:latest")
    replicas = config.get("replicas", 1)
    port = config.get("port", 80)
    namespace = config.get("namespace", "kubenet-experiment")
    
    # Create Deployment
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": app_name,
            "namespace": namespace,
            "labels": {"app": app_name}
        },
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": app_name}},
            "template": {
                "metadata": {"labels": {"app": app_name}},
                "spec": {
                    "containers": [{
                        "name": app_name,
                        "image": image,
                        "ports": [{"containerPort": port}],
                        "resources": {
                            "requests": {"cpu": "100m", "memory": "128Mi"},
                            "limits": {"cpu": "500m", "memory": "512Mi"}
                        }
                    }]
                }
            }
        }
    }
    
    # Create Service
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"{app_name}-service",
            "namespace": namespace,
            "labels": {"app": app_name}
        },
        "spec": {
            "selector": {"app": app_name},
            "ports": [{"port": 80, "targetPort": port}],
            "type": "ClusterIP"
        }
    }
    
    return [deployment, service]

async def deploy_resources(resources):
    """Deploy resources to Kubernetes"""
    results = []
    
    for resource in resources:
        try:
            # Create temporary YAML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(resource, f)
                temp_file = f.name
            
            print(f"📄 Deploying {resource['kind']}: {resource['metadata']['name']}")
            
            # Apply to Kubernetes
            result = subprocess.run(
                ['kubectl', 'apply', '-f', temp_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ Success: {result.stdout.strip()}")
                results.append({"success": True, "resource": resource['metadata']['name']})
            else:
                print(f"   ❌ Error: {result.stderr.strip()}")
                results.append({"success": False, "error": result.stderr.strip()})
            
            # Clean up temp file
            os.unlink(temp_file)
            
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append({"success": False, "error": str(e)})
    
    return results

async def check_deployment_status():
    """Check the status of deployed resources"""
    print("\n🔍 Checking pods...")
    pod_result = subprocess.run(
        ['kubectl', 'get', 'pods', '-n', 'kubenet-experiment'],
        capture_output=True,
        text=True
    )
    print(pod_result.stdout)
    
    print("\n🔍 Checking services...")
    service_result = subprocess.run(
        ['kubectl', 'get', 'services', '-n', 'kubenet-experiment'],
        capture_output=True,
        text=True
    )
    print(service_result.stdout)
    
    # Wait and check again
    print("\n⏳ Waiting 10 seconds for pods to start...")
    await asyncio.sleep(10)
    
    print("\n🔍 Checking pods again...")
    pod_result = subprocess.run(
        ['kubectl', 'get', 'pods', '-n', 'kubenet-experiment'],
        capture_output=True,
        text=True
    )
    print(pod_result.stdout)

async def call_ollama(prompt):
    """Call Ollama API"""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("response", "")
            else:
                raise Exception(f"Ollama API error: {response.status}")

def extract_json_from_response(response):
    """Extract JSON from LLM response"""
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"error": "No valid JSON found", "response": response}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "response": response}

if __name__ == "__main__":
    asyncio.run(test_single_deployment()) 