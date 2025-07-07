#!/usr/bin/env python3
"""
Improve CodeLlama Performance for Kubernetes YAML Generation
Tests different prompting strategies to see if we can fix the 0% success rate
"""

import asyncio
import json
import time
import yaml
import requests
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
class PromptTestResult:
    """Result from testing a prompting strategy"""
    strategy: str
    model: str
    scenario: str
    success: bool
    generation_time: float
    tokens_used: int
    yaml_quality: str
    generated_content: str
    error: Optional[str] = None


class CodeLlamaImprovement:
    """Test different strategies to improve CodeLlama performance"""
    
    def __init__(self):
        self.model = "codellama:latest"
        self.test_scenario = "Simple Web App"
        
        # Different prompting strategies to test
        self.strategies = {
            "original": self.get_original_prompt,
            "explicit_yaml": self.get_explicit_yaml_prompt,
            "few_shot": self.get_few_shot_prompt,
            "step_by_step": self.get_step_by_step_prompt,
            "template_based": self.get_template_based_prompt,
            "strict_format": self.get_strict_format_prompt
        }
    
    def get_original_prompt(self) -> str:
        """Original prompt that failed"""
        return """
Generate a complete Kubernetes YAML configuration for a simple web application with the following requirements:
- A deployment with an nginx container
- A service to expose the application
- Use port 80
- Set replicas to 2
- Include proper labels and selectors

Return only valid YAML configuration.
"""
    
    def get_explicit_yaml_prompt(self) -> str:
        """More explicit about YAML format requirements"""
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
    
    def get_few_shot_prompt(self) -> str:
        """Provide an example of what we want"""
        return """
Generate Kubernetes YAML for a simple web application.

Example format:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: example-app
  template:
    metadata:
      labels:
        app: example-app
    spec:
      containers:
      - name: example
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: example-service
spec:
  selector:
    app: example-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

Now generate similar YAML for:
- A deployment with nginx container
- A service to expose the application
- Use port 80
- Set replicas to 2
- Include proper labels and selectors

Return only the YAML content, starting with apiVersion:
"""
    
    def get_step_by_step_prompt(self) -> str:
        """Break it down into steps"""
        return """
Generate Kubernetes YAML configuration step by step:

Step 1: Create a Deployment resource
- apiVersion: apps/v1
- kind: Deployment
- name: nginx-app
- replicas: 2
- container: nginx:latest
- containerPort: 80
- labels: app=nginx-app

Step 2: Create a Service resource
- apiVersion: v1
- kind: Service
- name: nginx-service
- selector: app=nginx-app
- port: 80
- targetPort: 80

Output the complete YAML configuration. Start with apiVersion and do not include any explanations.
"""
    
    def get_template_based_prompt(self) -> str:
        """Use a template approach"""
        return """
Fill in this Kubernetes YAML template:

apiVersion: apps/v1
kind: Deployment
metadata:
  name: [APP_NAME]
  labels:
    app: [APP_LABEL]
spec:
  replicas: [REPLICA_COUNT]
  selector:
    matchLabels:
      app: [APP_LABEL]
  template:
    metadata:
      labels:
        app: [APP_LABEL]
    spec:
      containers:
      - name: [CONTAINER_NAME]
        image: [IMAGE]
        ports:
        - containerPort: [PORT]
---
apiVersion: v1
kind: Service
metadata:
  name: [SERVICE_NAME]
spec:
  selector:
    app: [APP_LABEL]
  ports:
  - port: [PORT]
    targetPort: [PORT]
  type: ClusterIP

Replace the placeholders with:
- APP_NAME: nginx-app
- APP_LABEL: nginx-app  
- REPLICA_COUNT: 2
- CONTAINER_NAME: nginx
- IMAGE: nginx:latest
- SERVICE_NAME: nginx-service
- PORT: 80

Return only the filled template without brackets or explanations.
"""
    
    def get_strict_format_prompt(self) -> str:
        """Very strict formatting instructions"""
        return """
IMPORTANT: You must respond with ONLY Kubernetes YAML. No explanations. No markdown. No code blocks.

Generate exactly this structure:

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-app
  labels:
    app: nginx-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx-app
  template:
    metadata:
      labels:
        app: nginx-app
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP

Start your response with "apiVersion:" immediately.
"""
    
    async def test_strategy(self, strategy_name: str) -> PromptTestResult:
        """Test a specific prompting strategy"""
        logger.info(f"🧪 Testing strategy: {strategy_name}")
        
        start_time = time.time()
        prompt = self.strategies[strategy_name]()
        
        try:
            # Call Ollama API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
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
                return PromptTestResult(
                    strategy=strategy_name,
                    model=self.model,
                    scenario=self.test_scenario,
                    success=False,
                    generation_time=time.time() - start_time,
                    tokens_used=0,
                    yaml_quality="API Error",
                    generated_content="",
                    error=f"API error: {response.status_code}"
                )
            
            result = response.json()
            generated_content = result.get("response", "")
            generation_time = time.time() - start_time
            
            # Analyze YAML quality
            success, quality = self.analyze_yaml_detailed(generated_content)
            tokens_used = len(generated_content.split()) + len(prompt.split())
            
            return PromptTestResult(
                strategy=strategy_name,
                model=self.model,
                scenario=self.test_scenario,
                success=success,
                generation_time=generation_time,
                tokens_used=tokens_used,
                yaml_quality=quality,
                generated_content=generated_content[:500] + "..." if len(generated_content) > 500 else generated_content
            )
            
        except Exception as e:
            return PromptTestResult(
                strategy=strategy_name,
                model=self.model,
                scenario=self.test_scenario,
                success=False,
                generation_time=time.time() - start_time,
                tokens_used=0,
                yaml_quality="Error",
                generated_content="",
                error=str(e)
            )
    
    def analyze_yaml_detailed(self, content: str) -> tuple[bool, str]:
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
                    return True, "Valid YAML but incomplete (missing service or deployment)"
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
    
    async def run_improvement_tests(self) -> Dict[str, Any]:
        """Run all improvement tests"""
        logger.info("🚀 Testing CodeLlama Improvement Strategies")
        logger.info("=" * 60)
        
        results = {
            "timestamp": time.time(),
            "model": self.model,
            "scenario": self.test_scenario,
            "strategies_tested": list(self.strategies.keys()),
            "results": {},
            "summary": {}
        }
        
        successful_strategies = []
        failed_strategies = []
        
        # Test each strategy
        for strategy_name in self.strategies.keys():
            test_result = await self.test_strategy(strategy_name)
            
            results["results"][strategy_name] = {
                "success": test_result.success,
                "generation_time": test_result.generation_time,
                "tokens_used": test_result.tokens_used,
                "yaml_quality": test_result.yaml_quality,
                "generated_sample": test_result.generated_content[:200] + "..." if len(test_result.generated_content) > 200 else test_result.generated_content,
                "error": test_result.error
            }
            
            if test_result.success:
                successful_strategies.append(strategy_name)
                logger.info(f"✅ {strategy_name}: SUCCESS - {test_result.yaml_quality}")
            else:
                failed_strategies.append(strategy_name)
                logger.info(f"❌ {strategy_name}: FAILED - {test_result.yaml_quality}")
        
        # Generate summary
        success_rate = (len(successful_strategies) / len(self.strategies)) * 100
        
        results["summary"] = {
            "total_strategies": len(self.strategies),
            "successful_strategies": successful_strategies,
            "failed_strategies": failed_strategies,
            "success_rate": success_rate,
            "improvement": f"Improved from 0% to {success_rate:.1f}%" if success_rate > 0 else "No improvement achieved"
        }
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print formatted summary"""
        print("\n" + "="*60)
        print("🎯 CODELLAMA IMPROVEMENT RESULTS")
        print("="*60)
        
        summary = results["summary"]
        print(f"\n📊 Overall Results:")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Strategies Tested: {summary['total_strategies']}")
        print(f"   {summary['improvement']}")
        
        if summary["successful_strategies"]:
            print(f"\n✅ Successful Strategies:")
            for strategy in summary["successful_strategies"]:
                result = results["results"][strategy]
                print(f"   • {strategy}: {result['yaml_quality']}")
        
        if summary["failed_strategies"]:
            print(f"\n❌ Failed Strategies:")
            for strategy in summary["failed_strategies"]:
                result = results["results"][strategy]
                print(f"   • {strategy}: {result['yaml_quality']}")
        
        print("\n💡 Key Insights:")
        if summary["success_rate"] > 0:
            print("   • CodeLlama CAN generate valid YAML with proper prompting")
            print("   • Prompt engineering significantly impacts model performance")
            print("   • Specific formatting instructions are crucial")
        else:
            print("   • CodeLlama appears fundamentally unsuited for YAML generation")
            print("   • Even improved prompting cannot overcome model limitations")
            print("   • Consider using different models for configuration tasks")
        
        print("\n" + "="*60)


async def main():
    """Run CodeLlama improvement tests"""
    tester = CodeLlamaImprovement()
    
    try:
        results = await tester.run_improvement_tests()
        tester.print_summary(results)
        
        # Save results
        with open(f"data/results/codellama_improvement_{int(time.time())}.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Improvement tests completed!")
        print(f"📁 Results saved to data/results/")
        
    except Exception as e:
        logger.error(f"❌ Improvement tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 