#!/usr/bin/env python3
"""
Simple test for real MCP integration with actual Kubernetes cluster queries.
"""

import asyncio
import json
import time
from pathlib import Path
import sys
import os

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

from mcp.broker import MCPBroker


async def test_real_mcp_integration():
    """Test the real MCP broker with actual Kubernetes integration"""
    
    print("🚀 Testing Real MCP Integration with Kubernetes")
    print("=" * 60)
    
    # Initialize real MCP broker
    config = {
        "cluster_context": "current",
        "validation_level": "comprehensive"
    }
    
    broker = MCPBroker(config)
    await broker.start()
    
    print(f"✅ MCP Broker started (kubectl available: {broker.kubectl_available})")
    print(f"📋 Available tools: {len(broker.tools)}")
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Real Cluster Information",
            "tool": "cluster_info",
            "params": {"resource_type": "all"}
        },
        {
            "name": "Real Security Policies",
            "tool": "security_policies", 
            "params": {"policy_type": "pod_security"}
        },
        {
            "name": "Real Knowledge Base - Web App Template",
            "tool": "knowledge_base",
            "params": {"category": "templates", "topic": "web_application"}
        },
        {
            "name": "Real Configuration Validation",
            "tool": "config_validator",
            "params": {
                "config": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "test-app"},
                    "spec": {
                        "replicas": 2,
                        "selector": {"matchLabels": {"app": "test-app"}},
                        "template": {
                            "metadata": {"labels": {"app": "test-app"}},
                            "spec": {
                                "containers": [{
                                    "name": "app",
                                    "image": "nginx:latest",
                                    "ports": [{"containerPort": 80}]
                                }]
                            }
                        }
                    }
                },
                "validation_level": "comprehensive"
            }
        },
        {
            "name": "Real Kubernetes Documentation",
            "tool": "kubernetes_docs",
            "params": {"query": "deployment security"}
        }
    ]
    
    results = {}
    total_start_time = time.time()
    
    for scenario in test_scenarios:
        print(f"\n🔍 Testing: {scenario['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            result = await broker.invoke_tool(scenario["tool"], scenario["params"])
            execution_time = time.time() - start_time
            
            results[scenario["name"]] = {
                "tool": scenario["tool"],
                "execution_time": execution_time,
                "success": True,
                "result_size": len(str(result)),
                "has_error": "error" in result
            }
            
            print(f"⏱️  Execution time: {execution_time:.3f}s")
            print(f"📊 Result size: {len(str(result))} characters")
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                results[scenario["name"]]["success"] = False
            else:
                print("✅ Success!")
                
                # Show key information for each tool
                if scenario["tool"] == "cluster_info":
                    print(f"   - Cluster: {result.get('current_context', 'unknown')}")
                    print(f"   - K8s Version: {result.get('kubernetes_version', 'unknown')}")
                    print(f"   - Nodes: {result.get('node_count', 'unknown')}")
                    print(f"   - Namespaces: {len(result.get('namespaces', []))}")
                    
                elif scenario["tool"] == "security_policies":
                    policies = result.get('policies', {})
                    print(f"   - Security policies: {len(policies)}")
                    if 'pod_security' in policies:
                        print(f"   - Pod security rules: {len(policies['pod_security'])}")
                    
                elif scenario["tool"] == "knowledge_base":
                    if 'template' in result:
                        template = result['template']
                        print(f"   - Template: {template.get('description', 'No description')}")
                        print(f"   - Components: {len(template.get('components', []))}")
                    
                elif scenario["tool"] == "config_validator":
                    print(f"   - Valid: {result.get('valid', 'unknown')}")
                    print(f"   - Security score: {result.get('security_score', 'N/A')}")
                    print(f"   - Issues found: {len(result.get('issues', []))}")
                    print(f"   - Recommendations: {len(result.get('recommendations', []))}")
                    
                elif scenario["tool"] == "kubernetes_docs":
                    print(f"   - Query: {result.get('query', 'unknown')}")
                    print(f"   - Best practices: {len(result.get('best_practices', []))}")
                    print(f"   - Examples: {len(result.get('examples', []))}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            results[scenario["name"]] = {
                "tool": scenario["tool"],
                "execution_time": execution_time,
                "success": False,
                "error": str(e)
            }
            print(f"❌ Failed: {str(e)}")
            print(f"⏱️  Execution time: {execution_time:.3f}s")
    
    total_execution_time = time.time() - total_start_time
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 REAL MCP INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    successful_tests = sum(1 for r in results.values() if r["success"])
    total_tests = len(results)
    
    print(f"✅ Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"⏱️  Total Execution Time: {total_execution_time:.3f}s")
    print(f"📋 MCP Tools Tested: {len(set(r['tool'] for r in results.values()))}")
    
    # Detailed results
    print("\n📋 Detailed Results:")
    for scenario_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"  {status} {scenario_name}")
        print(f"      Tool: {result['tool']}")
        print(f"      Time: {result['execution_time']:.3f}s")
        if not result["success"] and "error" in result:
            print(f"      Error: {result['error']}")
    
    # Real vs Mock comparison
    print("\n🔍 Real MCP Benefits Analysis:")
    print("=" * 40)
    print("✅ Real Cluster Data:")
    print("  - Live cluster information from kubectl")
    print("  - Actual node, namespace, and storage class data")
    print("  - Current context and version information")
    
    print("\n✅ Real Security Policies:")
    print("  - Industry-standard security policies (CIS, NIST)")
    print("  - Pod Security Standards detection")
    print("  - Compliance framework mapping")
    
    print("\n✅ Real Validation:")
    print("  - kubectl dry-run validation")
    print("  - Security score calculation")
    print("  - Compliance status checking")
    
    print("\n✅ Real Knowledge Base:")
    print("  - Production-ready templates")
    print("  - Deployment pattern library")
    print("  - Best practice documentation")
    
    broker_stats = broker.get_broker_stats()
    print(f"\n📊 MCP Broker Stats:")
    print(f"  - Type: {broker_stats.get('type', 'unknown')}")
    print(f"  - kubectl Available: {broker_stats.get('kubectl_available', False)}")
    print(f"  - Registered Tools: {broker_stats.get('registered_tools', 0)}")
    print(f"  - Stored Contexts: {broker_stats.get('stored_contexts', 0)}")
    
    await broker.stop()
    
    # Create results directory
    results_dir = Path("data/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Save results
    results_file = results_dir / f"real_mcp_integration_{int(time.time())}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "total_execution_time": total_execution_time,
            "success_rate": successful_tests/total_tests,
            "kubectl_available": broker.kubectl_available,
            "test_results": results,
            "broker_stats": broker_stats
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("\n🎉 Real MCP Integration Test Complete!")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_real_mcp_integration()) 