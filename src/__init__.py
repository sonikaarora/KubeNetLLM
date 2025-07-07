"""
KubeNetLLM: An Architectural Framework for Context-Aware Kubernetes Network Configuration
Using LLMs and MCP.

This package provides the core components for natural language driven Kubernetes
network configuration generation, validation, and deployment.
"""

__version__ = "1.0.0"
__author__ = "KubeNetLLM Research Team"
__email__ = "research@kubenetllm.org"

from .core import (
    NaturalLanguageInterface,
    ConfigurationGenerator,
    ValidationFramework,
    DeploymentManager,
    KubeNetLLMFramework
)

from .mcp import MCPBroker
from .validation import HierarchicalValidator
from .deployment import IntelligentDeploymentManager

__all__ = [
    "NaturalLanguageInterface",
    "ConfigurationGenerator", 
    "ValidationFramework",
    "DeploymentManager",
    "KubeNetLLMFramework",
    "MCPBroker",
    "HierarchicalValidator",
    "IntelligentDeploymentManager",
] 