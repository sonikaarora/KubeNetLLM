#!/usr/bin/env python3
"""
Real MCP Experiment Runner for KubeNetLLM Framework
Uses actual MCP integration with real Kubernetes cluster queries
"""

import asyncio
import json
import time
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup basic logging
import structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

from core.framework import KubeNetLLMFramework
from core.llm_providers import OllamaProvider
from mcp.broker import MCPBroker
from utils.metrics import MetricsCollector
import subprocess
import psutil


class RealMCPExperimentRunner:
    """Experiment runner using real MCP integration with Kubernetes"""
    
    def __init__(self):
        self.results = []
        self.metrics_collector = MetricsCollector()
        self.framework = None
        self.mcp_broker = None
        
    async def setup(self):
        """Setup the experiment environment"""
        print("🚀 Setting up Real MCP Experiment Runner")
        
        # Initialize MCP broker
        mcp_config = {
            "cluster_context": "current",
            "validation_level": "comprehensive"
        }
        
        self.mcp_broker = MCPBroker(mcp_config)
        await self.mcp_broker.start()
        
        # Initialize LLM provider
        llm_config = {
            "model": "llama3.2:3b",
            "base_url": "http://localhost:11434",
            "timeout": 120
        }
        
        llm_provider = OllamaProvider(llm_config)
        
        # Initialize framework with real MCP broker
        framework_config = {
            "llm_provider": llm_provider,
            "mcp_broker": self.mcp_broker,
            "deployment_namespace": "kubenet-experiment",
            "validation_enabled": True
        }
        
        self.framework = KubeNetLLMFramework(framework_config)
        
        print(f"✅ MCP Broker started (kubectl available: {self.mcp_broker.kubectl_available})")
        print(f"📋 Available MCP tools: {len(self.mcp_broker.tools)}")
        
    async def run_experiment(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single experiment scenario with real MCP integration"""
        
        print(f"\n🔍 Running: {scenario['name']}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Gather MCP context first
            mcp_context = await self._gather_mcp_context(scenario)
            
            # Generate configuration using framework with MCP context
            config_result = await self.framework.generate_configuration(
                prompt=scenario["prompt"],
                context=mcp_context
            )
            
            generation_time = time.time() - start_time
            
            # Deploy configuration
            deploy_start = time.time()
            deployment_result = await self.framework.deploy_configuration(
                config_result["config"]
            )
            deploy_time = time.time() - deploy_start
            
            # Collect metrics
            metrics = self.metrics_collector.collect_metrics()
            
            total_time = time.time() - start_time
            
            result = {
                "scenario": scenario["name"],
                "prompt": scenario["prompt"],
                "generation_time": generation_time,
                "deployment_time": deploy_time,
                "total_time": total_time,
                "success": True,
                "config_generated": bool(config_result.get("config")),
                "deployment_success": deployment_result.get("success", False),
                "mcp_context_used": len(mcp_context),
                "metrics": metrics,
                "token_usage": config_result.get("token_usage", {}),
                "mcp_tools_used": list(mcp_context.keys())
            }
            
            print(f"✅ Success! Generated in {generation_time:.3f}s, deployed in {deploy_time:.3f}s")
            print(f"📊 MCP tools used: {len(mcp_context)}")
            
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            result = {
                "scenario": scenario["name"],
                "prompt": scenario["prompt"],
                "generation_time": 0,
                "deployment_time": 0,
                "total_time": total_time,
                "success": False,
                "error": str(e),
                "mcp_context_used": 0,
                "metrics": {},
                "token_usage": {},
                "mcp_tools_used": []
            }
            
            print(f"❌ Failed: {str(e)}")
            
            return result
    
    async def _gather_mcp_context(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Gather context from MCP tools for the scenario"""
        context = {}
        
        # Get cluster information
        cluster_info = await self.mcp_broker.invoke_tool("cluster_info", {"resource_type": "all"})
        context["cluster_info"] = cluster_info
        
        # Get security policies
        security_policies = await self.mcp_broker.invoke_tool("security_policies", {"policy_type": "all"})
        context["security_policies"] = security_policies
        
        # Get relevant knowledge base templates
        app_type = "web_application" if "web" in scenario["prompt"].lower() else "microservice"
        knowledge_base = await self.mcp_broker.invoke_tool("knowledge_base", {
            "category": "templates",
            "topic": app_type
        })
        context["knowledge_base"] = knowledge_base
        
        # Get documentation
        docs = await self.mcp_broker.invoke_tool("kubernetes_docs", {"query": scenario["prompt"]})
        context["documentation"] = docs
        
        return context
    
    async def run_all_experiments(self):
        """Run all experiment scenarios"""
        
        scenarios = [
            {
                "name": "Simple Web Application",
                "prompt": "Create a simple web application with nginx, 2 replicas, and basic security"
            },
            {
                "name": "Microservice with Database",
                "prompt": "Deploy a microservice with Redis database, including persistent storage and security policies"
            },
            {
                "name": "Multi-Environment App",
                "prompt": "Create a web application that can be deployed across development, staging, and production environments"
            },
            {
                "name": "Security-Focused Application",
                "prompt": "Deploy a highly secure web application with strict security policies, non-root containers, and network policies"
            },
            {
                "name": "High-Availability Service",
                "prompt": "Create a high-availability service with multiple replicas, health checks, and load balancing"
            }
        ]
        
        print("🚀 Starting Real MCP Experiment Suite")
        print("=" * 60)
        
        experiment_start = time.time()
        
        for scenario in scenarios:
            result = await self.run_experiment(scenario)
            self.results.append(result)
            
            # Brief pause between scenarios
            await asyncio.sleep(1)
        
        total_experiment_time = time.time() - experiment_start
        
        # Generate summary
        await self._generate_summary(total_experiment_time)
        
        # Save results
        await self._save_results()
    
    async def _generate_summary(self, total_time: float):
        """Generate experiment summary"""
        
        print("\n" + "=" * 60)
        print("📊 REAL MCP EXPERIMENT SUMMARY")
        print("=" * 60)
        
        successful_experiments = sum(1 for r in self.results if r["success"])
        total_experiments = len(self.results)
        
        total_generation_time = sum(r["generation_time"] for r in self.results if r["success"])
        total_deployment_time = sum(r["deployment_time"] for r in self.results if r["success"])
        
        avg_generation_time = total_generation_time / successful_experiments if successful_experiments > 0 else 0
        avg_deployment_time = total_deployment_time / successful_experiments if successful_experiments > 0 else 0
        
        total_tokens = sum(r["token_usage"].get("total_tokens", 0) for r in self.results)
        
        print(f"✅ Success Rate: {successful_experiments}/{total_experiments} ({successful_experiments/total_experiments*100:.1f}%)")
        print(f"⏱️  Total Experiment Time: {total_time:.3f}s")
        print(f"📊 Average Generation Time: {avg_generation_time:.3f}s")
        print(f"📊 Average Deployment Time: {avg_deployment_time:.3f}s")
        print(f"🔢 Total Tokens Used: {total_tokens}")
        
        # MCP Integration Analysis
        print("\n🔍 MCP Integration Analysis:")
        print("-" * 40)
        
        mcp_tools_used = set()
        total_mcp_context = 0
        
        for result in self.results:
            if result["success"]:
                mcp_tools_used.update(result["mcp_tools_used"])
                total_mcp_context += result["mcp_context_used"]
        
        print(f"🛠️  MCP Tools Used: {len(mcp_tools_used)}")
        print(f"📋 Total MCP Context Items: {total_mcp_context}")
        print(f"🔧 MCP Tools: {', '.join(mcp_tools_used)}")
        
        # Detailed results
        print("\n📋 Detailed Results:")
        for result in self.results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"  {status} {result['scenario']}")
            print(f"      Generation: {result['generation_time']:.3f}s")
            print(f"      Deployment: {result['deployment_time']:.3f}s")
            print(f"      MCP Context: {result['mcp_context_used']} items")
            if not result["success"]:
                print(f"      Error: {result.get('error', 'Unknown error')}")
    
    async def _save_results(self):
        """Save experiment results to file"""
        
        results_dir = Path("data/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        results_file = results_dir / f"real_mcp_experiment_{timestamp}.json"
        
        # Include broker stats
        broker_stats = self.mcp_broker.get_broker_stats()
        
        results_data = {
            "timestamp": timestamp,
            "experiment_type": "real_mcp_integration",
            "kubectl_available": self.mcp_broker.kubectl_available,
            "mcp_broker_stats": broker_stats,
            "results": self.results,
            "summary": {
                "total_experiments": len(self.results),
                "successful_experiments": sum(1 for r in self.results if r["success"]),
                "total_generation_time": sum(r["generation_time"] for r in self.results if r["success"]),
                "total_deployment_time": sum(r["deployment_time"] for r in self.results if r["success"]),
                "total_tokens": sum(r["token_usage"].get("total_tokens", 0) for r in self.results),
                "mcp_tools_used": list(set().union(*(r["mcp_tools_used"] for r in self.results if r["success"])))
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Also save a summary markdown file
        summary_file = results_dir / f"real_mcp_experiment_summary_{timestamp}.md"
        await self._save_markdown_summary(summary_file, results_data)
        
        print(f"📄 Summary saved to: {summary_file}")
    
    async def _save_markdown_summary(self, file_path: Path, data: Dict[str, Any]):
        """Save a markdown summary of the experiment results"""
        
        with open(file_path, 'w') as f:
            f.write("# Real MCP Integration Experiment Results\n\n")
            f.write(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['timestamp']))}\n\n")
            
            f.write("## Summary\n\n")
            summary = data["summary"]
            f.write(f"- **Total Experiments:** {summary['total_experiments']}\n")
            f.write(f"- **Successful Experiments:** {summary['successful_experiments']}\n")
            f.write(f"- **Success Rate:** {summary['successful_experiments']/summary['total_experiments']*100:.1f}%\n")
            f.write(f"- **Total Generation Time:** {summary['total_generation_time']:.3f}s\n")
            f.write(f"- **Total Deployment Time:** {summary['total_deployment_time']:.3f}s\n")
            f.write(f"- **Total Tokens Used:** {summary['total_tokens']}\n")
            f.write(f"- **MCP Tools Used:** {', '.join(summary['mcp_tools_used'])}\n\n")
            
            f.write("## MCP Integration\n\n")
            broker_stats = data["mcp_broker_stats"]
            f.write(f"- **kubectl Available:** {broker_stats['kubectl_available']}\n")
            f.write(f"- **MCP Broker Type:** {broker_stats['type']}\n")
            f.write(f"- **Registered Tools:** {broker_stats['registered_tools']}\n\n")
            
            f.write("## Detailed Results\n\n")
            f.write("| Scenario | Success | Generation Time | Deployment Time | MCP Context |\n")
            f.write("|----------|---------|----------------|----------------|-------------|\n")
            
            for result in data["results"]:
                status = "✅" if result["success"] else "❌"
                f.write(f"| {result['scenario']} | {status} | {result['generation_time']:.3f}s | {result['deployment_time']:.3f}s | {result['mcp_context_used']} |\n")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mcp_broker:
            await self.mcp_broker.stop()
            print("🧹 MCP Broker stopped")


async def main():
    """Main experiment runner"""
    
    runner = RealMCPExperimentRunner()
    
    try:
        await runner.setup()
        await runner.run_all_experiments()
        
    except KeyboardInterrupt:
        print("\n🛑 Experiment interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Experiment failed: {str(e)}")
        
    finally:
        await runner.cleanup()
        print("\n🎉 Real MCP Experiment Complete!")


if __name__ == "__main__":
    asyncio.run(main()) 