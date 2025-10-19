#!/usr/bin/env python3
"""
MCP-Enabled KubeNetLLM Experiment Runner
Uses the full framework with actual MCP integration
"""

import asyncio
import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.framework import KubeNetLLMFramework
from utils.config import ConfigManager
import psutil
import subprocess

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPEnabledExperimentRunner:
    """Runner that uses full KubeNetLLM framework with MCP integration"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.results_dir = Path("data/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = ConfigManager(config_path)
        
        # Framework will be initialized
        self.framework = None
        
        # Experimental scenarios
        self.scenarios = {
            "Simple Web App": {
                "description": "Deploy a simple web application with basic routing",
                "requirements": [
                    "Single deployment with nginx",
                    "ClusterIP service on port 80",
                    "Basic resource limits"
                ],
                "complexity": "low"
            },
            "Microservices": {
                "description": "Deploy a microservices architecture with multiple services",
                "requirements": [
                    "Frontend deployment",
                    "Backend API deployment", 
                    "Database deployment",
                    "Service mesh configuration",
                    "Inter-service communication"
                ],
                "complexity": "high"
            },
            "Multi-Environment": {
                "description": "Deploy application with dev, staging, and production environments",
                "requirements": [
                    "Namespace separation",
                    "Environment-specific configurations",
                    "Resource quotas",
                    "Network policies"
                ],
                "complexity": "medium"
            },
            "Security-Focused": {
                "description": "Deploy with comprehensive security policies",
                "requirements": [
                    "Pod security policies",
                    "Network segmentation",
                    "RBAC configuration",
                    "Secret management",
                    "Security scanning"
                ],
                "complexity": "high"
            },
            "Edge Cases": {
                "description": "Handle edge cases and corner scenarios",
                "requirements": [
                    "Custom resource definitions",
                    "StatefulSet deployments",
                    "Persistent volumes",
                    "Init containers",
                    "Complex networking"
                ],
                "complexity": "medium"
            }
        }
        
        logger.info("MCP-Enabled Experiment Runner initialized")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        # Check Ollama
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error("❌ Ollama is not running")
                return False
        except Exception as e:
            logger.error(f"❌ Ollama check failed: {e}")
            return False
        
        # Check Kubernetes
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.error("❌ Kubernetes cluster is not available")
                return False
        except Exception as e:
            logger.error(f"❌ Kubernetes check failed: {e}")
            return False
        
        logger.info("✅ All prerequisites met")
        return True
    
    async def initialize_framework(self) -> bool:
        """Initialize the KubeNetLLM framework with MCP"""
        try:
            logger.info("🔧 Initializing KubeNetLLM framework with MCP integration...")
            self.framework = KubeNetLLMFramework(self.config_path)
            await self.framework.initialize()
            logger.info("✅ Framework initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Framework initialization failed: {e}")
            return False
    
    def get_resource_utilization(self) -> Dict[str, Any]:
        """Get system resource utilization"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024
        }
    
    async def run_scenario_with_mcp(self, scenario_name: str, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a scenario using the full framework with MCP integration"""
        logger.info(f"🚀 Running scenario with MCP: {scenario_name}")
        
        # Track resource utilization
        resource_before = self.get_resource_utilization()
        
        # Create natural language input
        description = scenario_config.get("description", "")
        requirements = scenario_config.get("requirements", [])
        
        nl_input = f"{description}\n\nRequirements:\n"
        for req in requirements:
            nl_input += f"- {req}\n"
        
        # Run through the complete framework pipeline
        start_time = time.time()
        
        try:
            # This will use the full framework with MCP integration
            result = await self.framework.generate_configuration(
                natural_language_input=nl_input,
                context={"scenario": scenario_name, "complexity": scenario_config.get("complexity", "medium")}
            )
            
            total_time = time.time() - start_time
            
            # Track resource utilization after
            resource_after = self.get_resource_utilization()
            
            # Extract real metrics from the framework result
            metrics = {
                "scenario": scenario_name,
                "success": result.success,
                "total_time": total_time,
                "generation_time": result.metrics.get("generation_time", 0),
                "validation_time": result.metrics.get("validation_time", 0),
                "deployment_time": result.metrics.get("deployment_time", 0),
                "api_calls": result.metrics.get("api_calls", 0),
                "tokens_used": result.metrics.get("tokens_used", 0),
                "prompt_tokens": result.metrics.get("prompt_tokens", 0),
                "completion_tokens": result.metrics.get("completion_tokens", 0),
                "mcp_calls": result.metrics.get("mcp_calls", 0),
                "mcp_tools_used": result.metrics.get("mcp_tools_used", []),
                "configurations_generated": len(result.configurations) if result.configurations else 0,
                "validation_results": result.validation_results if result.validation_results else {},
                "deployment_results": result.deployment_results if result.deployment_results else {},
                "resource_utilization": {
                    "cpu_before": resource_before["cpu_percent"],
                    "cpu_after": resource_after["cpu_percent"],
                    "memory_before": resource_before["memory_percent"],
                    "memory_after": resource_after["memory_percent"],
                    "memory_mb_before": resource_before["memory_used_mb"],
                    "memory_mb_after": resource_after["memory_used_mb"]
                }
            }
            
            logger.info(f"✅ Scenario {scenario_name} completed successfully")
            logger.info(f"📊 MCP calls: {metrics['mcp_calls']}, Tools used: {metrics['mcp_tools_used']}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Scenario {scenario_name} failed: {e}")
            return {
                "scenario": scenario_name,
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """Run all scenarios with MCP integration"""
        results = []
        
        logger.info("🚀 Starting MCP-Enabled KubeNetLLM Experiments")
        logger.info("=" * 60)
        
        for scenario_name, scenario_config in self.scenarios.items():
            try:
                result = await self.run_scenario_with_mcp(scenario_name, scenario_config)
                results.append(result)
                
                # Brief pause between scenarios
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Scenario {scenario_name} failed: {e}")
                results.append({
                    "scenario": scenario_name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def generate_mcp_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate MCP-specific analysis"""
        total_mcp_calls = sum(r.get("mcp_calls", 0) for r in results)
        all_mcp_tools = []
        for r in results:
            if r.get("mcp_tools_used"):
                all_mcp_tools.extend(r["mcp_tools_used"])
        
        unique_tools = list(set(all_mcp_tools))
        
        return {
            "total_mcp_calls": total_mcp_calls,
            "average_mcp_calls_per_scenario": total_mcp_calls / len(results) if results else 0,
            "unique_mcp_tools_used": unique_tools,
            "mcp_tool_usage_count": len(all_mcp_tools),
            "scenarios_using_mcp": sum(1 for r in results if r.get("mcp_calls", 0) > 0)
        }
    
    def generate_enhanced_tables(self, results: List[Dict[str, Any]]) -> None:
        """Generate enhanced tables with MCP data"""
        
        # Enhanced Performance Metrics with MCP
        print("\n" + "="*80)
        print("TABLE III: PERFORMANCE METRICS WITH MCP INTEGRATION")
        print("="*80)
        print(f"{'Scenario':<20} {'Gen Time':<10} {'API Calls':<10} {'Tokens':<10} {'MCP Calls':<10} {'Success':<10}")
        print("-" * 80)
        
        total_time = 0
        total_api_calls = 0
        total_tokens = 0
        total_mcp_calls = 0
        successful = 0
        
        for result in results:
            if result.get("success", False):
                successful += 1
                
            gen_time = result.get("generation_time", 0)
            api_calls = result.get("api_calls", 0)
            tokens = result.get("tokens_used", 0)
            mcp_calls = result.get("mcp_calls", 0)
            success = "✅" if result.get("success", False) else "❌"
            
            print(f"{result['scenario']:<20} {gen_time:<10.2f} {api_calls:<10} {tokens:<10} {mcp_calls:<10} {success:<10}")
            
            total_time += gen_time
            total_api_calls += api_calls
            total_tokens += tokens
            total_mcp_calls += mcp_calls
        
        print("-" * 80)
        success_rate = (successful / len(results)) * 100 if results else 0
        print(f"{'TOTAL':<20} {total_time:<10.2f} {total_api_calls:<10} {total_tokens:<10} {total_mcp_calls:<10} {success_rate:<10.1f}%")
        
        # MCP Usage Analysis
        print("\n" + "="*80)
        print("TABLE IV: MCP USAGE ANALYSIS")
        print("="*80)
        print(f"{'Scenario':<20} {'MCP Calls':<10} {'Tools Used':<30} {'Context Quality':<15}")
        print("-" * 80)
        
        for result in results:
            mcp_calls = result.get("mcp_calls", 0)
            tools_used = ", ".join(result.get("mcp_tools_used", [])[:2])  # First 2 tools
            if len(result.get("mcp_tools_used", [])) > 2:
                tools_used += "..."
            context_quality = "High" if mcp_calls >= 3 else "Medium" if mcp_calls >= 1 else "Low"
            
            print(f"{result['scenario']:<20} {mcp_calls:<10} {tools_used:<30} {context_quality:<15}")
        
        # Enhanced Validation with MCP
        print("\n" + "="*80)
        print("TABLE V: ENHANCED VALIDATION WITH MCP")
        print("="*80)
        print(f"{'Scenario':<20} {'Pass Rate':<10} {'Errors':<8} {'Warnings':<10} {'MCP Enhanced':<12}")
        print("-" * 80)
        
        for result in results:
            validation = result.get("validation_results", {})
            pass_rate = validation.get("pass_rate", 0)
            errors = validation.get("total_errors", 0)
            warnings = validation.get("total_warnings", 0)
            mcp_enhanced = "✅" if result.get("mcp_calls", 0) > 0 else "❌"
            
            print(f"{result['scenario']:<20} {pass_rate:<10.1f} {errors:<8} {warnings:<10} {mcp_enhanced:<12}")
        
        print("="*80)
    
    def save_results(self, results: List[Dict[str, Any]]) -> str:
        """Save results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mcp_enabled_results_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📄 Results saved to: {filepath}")
        return str(filepath)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.framework:
            await self.framework.cleanup()

async def main():
    """Main execution function"""
    runner = MCPEnabledExperimentRunner()
    
    # Check prerequisites
    if not runner.check_prerequisites():
        logger.error("❌ Prerequisites not met")
        return
    
    # Initialize framework
    if not await runner.initialize_framework():
        logger.error("❌ Framework initialization failed")
        return
    
    try:
        # Run experiments
        results = await runner.run_all_scenarios()
        
        # Generate MCP analysis
        mcp_analysis = runner.generate_mcp_analysis(results)
        
        # Generate enhanced tables
        runner.generate_enhanced_tables(results)
        
        # Print MCP analysis
        print("\n" + "="*80)
        print("MCP INTEGRATION ANALYSIS")
        print("="*80)
        print(f"Total MCP Calls: {mcp_analysis['total_mcp_calls']}")
        print(f"Average MCP Calls per Scenario: {mcp_analysis['average_mcp_calls_per_scenario']:.1f}")
        print(f"Unique MCP Tools Used: {', '.join(mcp_analysis['unique_mcp_tools_used'])}")
        print(f"Scenarios Using MCP: {mcp_analysis['scenarios_using_mcp']}/{len(results)}")
        
        # Save results
        results_file = runner.save_results(results)
        
        print(f"\n🎉 MCP-enabled experiments completed!")
        print(f"📊 Results saved to: {results_file}")
        print(f"✅ Success rate: {sum(1 for r in results if r.get('success', False))}/{len(results)} scenarios")
        
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 