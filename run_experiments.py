#!/usr/bin/env python3
"""
KubeNetLLM Experimental Framework Runner
========================================

This script runs all experimental scenarios from the KubeNetLLM research paper
and generates results in the format expected by the paper.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from experiments.runner import ExperimentRunner
from src.utils.logging import setup_logging


def print_header():
    """Print experiment header"""
    print("=" * 80)
    print("KubeNetLLM Experimental Framework")
    print("An Architectural Framework for Context-Aware Kubernetes Network Configuration")
    print("Using LLMs and Model Context Protocol (MCP)")
    print("=" * 80)
    print(f"Experiment started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def create_experiment_config():
    """Create experiment configuration"""
    return {
        "llm": {
            "providers": {
                "openai": {
                    "api_key": os.getenv("OPENAI_API_KEY", ""),
                    "model": "gpt-4",
                    "max_tokens": 4096,
                    "temperature": 0.1
                },
                "anthropic": {
                    "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 4096,
                    "temperature": 0.1
                }
            },
            "default_provider": "openai"
        },
        "mcp": {
            "enabled": True,
            "mock_mode": True,  # Use mock mode for testing
            "tools": [
                "kubernetes_docs",
                "cluster_info", 
                "security_policies",
                "knowledge_base",
                "config_validator"
            ]
        },
        "validation": {
            "levels": ["syntactic", "semantic", "security", "best_practices"],
            "strict_mode": True,
            "fail_fast": False
        },
        "deployment": {
            "dry_run": True,
            "progressive": True,
            "rollback_enabled": True,
            "safety_checks": [
                "cluster_connectivity",
                "namespace_exists",
                "rbac_permissions",
                "resource_quotas"
            ]
        },
        "metrics": {
            "collect_system_metrics": True,
            "collect_llm_metrics": True,
            "prometheus_enabled": False
        }
    }


async def run_experiments():
    """Run all experiments and generate results"""
    print_header()
    
    # Setup logging
    setup_logging()
    
    # Create experiment configuration
    config = create_experiment_config()
    
    # Initialize experiment runner
    runner = ExperimentRunner(config)
    
    try:
        # Run all experiments
        results = await runner.run_all_experiments()
        
        # Print summary
        print("\n" + "=" * 80)
        print("EXPERIMENT SUMMARY")
        print("=" * 80)
        
        summary = results.get("summary", {})
        print(f"Total Scenarios: {summary.get('total_scenarios', 0)}")
        print(f"Overall Success Rate: {summary.get('overall_success_rate', 0):.1f}%")
        print(f"Total Execution Time: {summary.get('total_execution_time', 0):.2f}s")
        print(f"Average Generation Time: {summary.get('avg_execution_time', 0):.2f}s")
        print(f"Total API Calls: {summary.get('total_api_calls', 0):.0f}")
        print(f"Total Tokens Used: {summary.get('total_tokens', 0):.0f}")
        
        validation_summary = summary.get("validation_summary", {})
        print(f"Average Validation Pass Rate: {validation_summary.get('avg_pass_rate', 0):.1f}%")
        print(f"Total Errors Detected: {validation_summary.get('total_errors', 0):.0f}")
        print(f"Total Warnings: {validation_summary.get('total_warnings', 0):.0f}")
        print(f"Total Recommendations: {validation_summary.get('total_recommendations', 0):.0f}")
        
        print("\n" + "=" * 80)
        print("RESULTS GENERATED")
        print("=" * 80)
        
        results_dir = Path("data/results")
        
        # List generated files
        generated_files = [
            "experiment_results.json",
            "experiment_summary.csv",
            "experiment_report.md",
            "table3_performance_metrics.csv",
            "table4_validation_metrics.csv",
            "table5_resource_utilization.csv",
            "performance_dashboard.png",
            "mcp_comparison.png",
            "validation_breakdown.png"
        ]
        
        print("Generated files:")
        for file_name in generated_files:
            file_path = results_dir / file_name
            if file_path.exists():
                print(f"  ✓ {file_name}")
            else:
                print(f"  ✗ {file_name} (missing)")
        
        print(f"\nResults directory: {results_dir.absolute()}")
        print(f"Report: {results_dir / 'experiment_report.md'}")
        print(f"Paper tables: table3_*.csv, table4_*.csv, table5_*.csv")
        print(f"Visualizations: *.png files")
        
        print("\n" + "=" * 80)
        print("PAPER FORMAT RESULTS")
        print("=" * 80)
        
        # Print paper format tables
        print_paper_tables(results_dir)
        
        return results
        
    except Exception as e:
        print(f"\nERROR: Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_paper_tables(results_dir: Path):
    """Print tables in paper format"""
    try:
        import pandas as pd
        
        # Table III: Configuration Generation Performance Metrics
        table3_file = results_dir / "table3_performance_metrics.csv"
        if table3_file.exists():
            print("\nTable III: Configuration Generation Performance Metrics")
            print("-" * 60)
            df = pd.read_csv(table3_file)
            print(df.to_string(index=False))
        
        # Table IV: Validation Framework Error Detection Rates
        table4_file = results_dir / "table4_validation_metrics.csv"
        if table4_file.exists():
            print("\nTable IV: Validation Framework Error Detection Rates")
            print("-" * 60)
            df = pd.read_csv(table4_file)
            print(df.to_string(index=False))
        
        # Table V: Local Resource Utilization
        table5_file = results_dir / "table5_resource_utilization.csv"
        if table5_file.exists():
            print("\nTable V: Local Resource Utilization During Configuration Generation")
            print("-" * 60)
            df = pd.read_csv(table5_file)
            print(df.to_string(index=False))
        
    except ImportError:
        print("\nPandas not available - table files generated but not displayed")
    except Exception as e:
        print(f"\nError displaying tables: {e}")


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("ERROR: Python 3.9 or higher required")
        return False
    
    # Check required packages
    required_packages = [
        "asyncio", "pandas", "matplotlib", "seaborn", "structlog",
        "yaml", "openai", "anthropic", "kubernetes", "rich"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"ERROR: Missing required packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    # Check directories
    required_dirs = ["src", "experiments", "config", "data"]
    for directory in required_dirs:
        if not Path(directory).exists():
            print(f"ERROR: Directory {directory} not found")
            return False
    
    print("✓ All prerequisites met")
    return True


def main():
    """Main entry point"""
    if not check_prerequisites():
        sys.exit(1)
    
    try:
        # Run experiments
        results = asyncio.run(run_experiments())
        
        if results:
            print("\n🎉 Experiments completed successfully!")
            print("\nNext steps:")
            print("1. Review the experiment report: data/results/experiment_report.md")
            print("2. Analyze the paper tables: data/results/table*.csv")
            print("3. View visualizations: data/results/*.png")
            print("4. Use results in your research paper")
        else:
            print("\n❌ Experiments failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 