"""
Hierarchical Validation Framework - Component 3 of KubeNetLLM architecture.
"""

import asyncio
import yaml
import json
import base64
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

import structlog
from jsonschema import validate, ValidationError
from kubernetes import client, config as k8s_config

from ..utils.exceptions import ValidationError as KubeNetValidationError

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of validation check"""
    level: str
    passed: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    details: Dict[str, Any]


class ValidationFramework:
    """
    Hierarchical Validation Framework - Component 3 of KubeNetLLM architecture.
    Multi-layer validation ensuring configuration correctness and security.
    """

    def __init__(self, config: Dict[str, Any], mcp_broker=None):
        """
        Initialize the Validation Framework.
        
        Args:
            config: Validation configuration
            mcp_broker: MCP broker instance
        """
        self.config = config
        self.mcp_broker = mcp_broker
        self.logger = structlog.get_logger(__name__)
        self.k8s_client = self._init_k8s_client()
        
        # Validation levels
        self.validation_levels = config.get("levels", [
            "syntactic", "semantic", "security", "best_practices"
        ])
        
        # Load validation schemas
        self.schemas = self._load_validation_schemas()
        
        self.logger.info("Validation Framework initialized",
                        levels=self.validation_levels)

    def _init_k8s_client(self):
        """Initialize Kubernetes client"""
        try:
            k8s_config.load_kube_config()
            return client.ApiClient()
        except Exception as e:
            self.logger.warning("Could not load Kubernetes config", error=str(e))
            return None

    def _load_validation_schemas(self) -> Dict[str, Dict]:
        """Load Kubernetes API schemas for validation"""
        # Simplified schemas for common resources
        return {
            "Deployment": {
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {
                    "apiVersion": {"type": "string"},
                    "kind": {"const": "Deployment"},
                    "metadata": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "namespace": {"type": "string"}
                        }
                    },
                    "spec": {
                        "type": "object",
                        "required": ["selector", "template"],
                        "properties": {
                            "replicas": {"type": "integer", "minimum": 1},
                            "selector": {"type": "object"},
                            "template": {"type": "object"}
                        }
                    }
                }
            },
            "Service": {
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {
                    "apiVersion": {"type": "string"},
                    "kind": {"const": "Service"},
                    "metadata": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "namespace": {"type": "string"}
                        }
                    },
                    "spec": {
                        "type": "object",
                        "required": ["selector", "ports"],
                        "properties": {
                            "selector": {"type": "object"},
                            "ports": {"type": "array"},
                            "type": {"type": "string"}
                        }
                    }
                }
            }
        }

    async def validate_configurations(self, 
                                    configurations: List[Dict[str, Any]],
                                    requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform hierarchical validation on configurations.
        
        Args:
            configurations: List of Kubernetes configuration dictionaries
            requirements: Original requirements for context
            
        Returns:
            Comprehensive validation results
        """
        self.logger.info("Starting hierarchical validation",
                        config_count=len(configurations))
        
        validation_results = {
            "overall_valid": True,
            "pass_rate": 0.0,
            "levels": {},
            "summary": {
                "total_errors": 0,
                "total_warnings": 0,
                "total_recommendations": 0
            },
            "configurations": []
        }
        
        # Validate each configuration
        for i, config in enumerate(configurations):
            config_results = await self._validate_single_configuration(config, requirements)
            validation_results["configurations"].append(config_results)
            
            # Aggregate results
            for level, result in config_results.items():
                if level not in validation_results["levels"]:
                    validation_results["levels"][level] = {
                        "passed": 0,
                        "failed": 0,
                        "errors": [],
                        "warnings": [],
                        "recommendations": []
                    }
                
                if isinstance(result, dict) and "passed" in result:
                    if result["passed"]:
                        validation_results["levels"][level]["passed"] += 1
                    else:
                        validation_results["levels"][level]["failed"] += 1
                        validation_results["overall_valid"] = False
                    
                    validation_results["levels"][level]["errors"].extend(result.get("errors", []))
                    validation_results["levels"][level]["warnings"].extend(result.get("warnings", []))
                    validation_results["levels"][level]["recommendations"].extend(result.get("recommendations", []))
        
        # Calculate summary statistics
        total_configs = len(configurations)
        passed_configs = sum(
            1 for config_result in validation_results["configurations"]
            if all(
                level_result.get("passed", False) if isinstance(level_result, dict) else True
                for level_result in config_result.values()
            )
        )
        
        validation_results["pass_rate"] = (passed_configs / total_configs * 100) if total_configs > 0 else 0
        
        # Count totals
        for level_data in validation_results["levels"].values():
            validation_results["summary"]["total_errors"] += len(level_data["errors"])
            validation_results["summary"]["total_warnings"] += len(level_data["warnings"])
            validation_results["summary"]["total_recommendations"] += len(level_data["recommendations"])
        
        self.logger.info("Hierarchical validation completed",
                        overall_valid=validation_results["overall_valid"],
                        pass_rate=validation_results["pass_rate"])
        
        return validation_results

    async def _validate_single_configuration(self, 
                                           config: Dict[str, Any],
                                           requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate a single configuration through all levels"""
        results = {}
        
        # Level 1: Syntactic Validation
        if "syntactic" in self.validation_levels:
            results["syntactic"] = await self._validate_syntactic(config)
        
        # Level 2: Semantic Validation
        if "semantic" in self.validation_levels:
            results["semantic"] = await self._validate_semantic(config, requirements)
        
        # Level 3: Security Validation
        if "security" in self.validation_levels:
            results["security"] = await self._validate_security(config)
        
        # Level 4: Best Practices
        if "best_practices" in self.validation_levels:
            results["best_practices"] = await self._validate_best_practices(config)
        
        return results

    async def _validate_syntactic(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Level 1: Syntactic validation - YAML structure and basic Kubernetes API compliance"""
        result = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            # Check required fields
            required_fields = ["apiVersion", "kind", "metadata"]
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                result["passed"] = False
                result["errors"].append(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Validate against schema if available
            kind = config.get("kind")
            if kind in self.schemas:
                try:
                    validate(instance=config, schema=self.schemas[kind])
                except ValidationError as e:
                    result["passed"] = False
                    result["errors"].append(f"Schema validation failed: {e.message}")
            
            # Check metadata
            metadata = config.get("metadata", {})
            if not metadata.get("name"):
                result["passed"] = False
                result["errors"].append("Metadata must include a name")
            
            # Validate name format (DNS subdomain)
            name = metadata.get("name", "")
            if name and not self._is_valid_dns_name(name):
                result["passed"] = False
                result["errors"].append(f"Invalid name format: {name}")
            
            # Check API version format
            api_version = config.get("apiVersion", "")
            if api_version and "/" not in api_version and api_version != "v1":
                if not api_version.startswith("v"):
                    result["warnings"].append(f"Unusual API version format: {api_version}")
            
        except Exception as e:
            result["passed"] = False
            result["errors"].append(f"Syntactic validation error: {str(e)}")
        
        return result

    async def _validate_semantic(self, 
                                config: Dict[str, Any],
                                requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Level 2: Semantic validation - Resource relationships and dependencies"""
        result = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        kind = config.get("kind")
        
        try:
            if kind == "Deployment":
                await self._validate_deployment_semantics(config, result)
            elif kind == "Service":
                await self._validate_service_semantics(config, result)
            elif kind == "NetworkPolicy":
                await self._validate_network_policy_semantics(config, result)
            elif kind == "Ingress":
                await self._validate_ingress_semantics(config, result)
            
            # Check resource relationships if MCP is available
            if self.mcp_broker:
                await self._validate_resource_relationships(config, result)
                
        except Exception as e:
            result["passed"] = False
            result["errors"].append(f"Semantic validation error: {str(e)}")
        
        return result

    async def _validate_deployment_semantics(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Deployment semantic correctness"""
        spec = config.get("spec", {})
        template = spec.get("template", {})
        template_spec = template.get("spec", {})
        
        # Check selector matches template labels
        selector = spec.get("selector", {}).get("matchLabels", {})
        template_labels = template.get("metadata", {}).get("labels", {})
        
        for key, value in selector.items():
            if template_labels.get(key) != value:
                result["passed"] = False
                result["errors"].append(
                    f"Selector label {key}={value} doesn't match template label {key}={template_labels.get(key)}"
                )
        
        # Check container specifications
        containers = template_spec.get("containers", [])
        if not containers:
            result["passed"] = False
            result["errors"].append("Deployment must have at least one container")
        
        for container in containers:
            if not container.get("image"):
                result["passed"] = False
                result["errors"].append(f"Container {container.get('name', 'unnamed')} missing image")
            
            # Check for latest tag
            image = container.get("image", "")
            if image.endswith(":latest") or ":" not in image:
                result["warnings"].append(
                    f"Container {container.get('name')} uses 'latest' tag, consider specific version"
                )

    async def _validate_service_semantics(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Service semantic correctness"""
        spec = config.get("spec", {})
        
        # Check selector
        selector = spec.get("selector", {})
        if not selector:
            result["warnings"].append("Service has no selector, it may not route traffic to any pods")
        
        # Check ports
        ports = spec.get("ports", [])
        if not ports:
            result["passed"] = False
            result["errors"].append("Service must define at least one port")
        
        # Check for port conflicts
        port_numbers = [port.get("port") for port in ports if port.get("port")]
        if len(port_numbers) != len(set(port_numbers)):
            result["passed"] = False
            result["errors"].append("Service has duplicate port numbers")

    async def _validate_network_policy_semantics(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate NetworkPolicy semantic correctness"""
        spec = config.get("spec", {})
        
        # Check pod selector
        pod_selector = spec.get("podSelector", {})
        if not pod_selector:
            result["warnings"].append("NetworkPolicy with empty podSelector affects all pods in namespace")
        
        # Check policy types
        policy_types = spec.get("policyTypes", [])
        if not policy_types:
            result["warnings"].append("NetworkPolicy should specify policyTypes")

    async def _validate_ingress_semantics(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Ingress semantic correctness"""
        spec = config.get("spec", {})
        
        # Check rules
        rules = spec.get("rules", [])
        if not rules:
            result["warnings"].append("Ingress has no rules defined")
        
        # Check TLS configuration
        tls = spec.get("tls", [])
        if not tls:
            result["recommendations"].append("Consider adding TLS configuration for HTTPS")

    async def _validate_resource_relationships(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate relationships with other resources via MCP"""
        try:
            # This would use MCP to check cluster state
            # For now, we'll simulate the check
            pass
        except Exception as e:
            result["warnings"].append(f"Could not validate resource relationships: {str(e)}")

    async def _validate_security(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Level 3: Security validation"""
        result = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        kind = config.get("kind")
        
        try:
            if kind == "Deployment":
                await self._validate_deployment_security(config, result)
            elif kind == "Service":
                await self._validate_service_security(config, result)
            elif kind == "NetworkPolicy":
                await self._validate_network_policy_security(config, result)
            
            # Get security policies from MCP if available
            if self.mcp_broker:
                await self._validate_against_security_policies(config, result)
                
        except Exception as e:
            result["passed"] = False
            result["errors"].append(f"Security validation error: {str(e)}")
        
        return result

    async def _validate_deployment_security(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Deployment security configuration"""
        spec = config.get("spec", {})
        template = spec.get("template", {})
        template_spec = template.get("spec", {})
        
        # Check pod security context
        security_context = template_spec.get("securityContext", {})
        if not security_context:
            result["warnings"].append("Pod missing security context")
        else:
            # Check for root user
            if security_context.get("runAsUser") == 0:
                result["errors"].append("Pod runs as root user (UID 0)")
                result["passed"] = False
            
            if security_context.get("runAsNonRoot") is False:
                result["warnings"].append("Pod allows running as root")
            
            if not security_context.get("readOnlyRootFilesystem"):
                result["recommendations"].append("Consider setting readOnlyRootFilesystem: true")
        
        # Check container security contexts
        containers = template_spec.get("containers", [])
        for container in containers:
            container_sc = container.get("securityContext", {})
            
            if not container_sc:
                result["warnings"].append(f"Container {container.get('name')} missing security context")
                continue
            
            # Check privilege escalation
            if container_sc.get("allowPrivilegeEscalation", True):
                result["warnings"].append(
                    f"Container {container.get('name')} allows privilege escalation"
                )
            
            # Check capabilities
            capabilities = container_sc.get("capabilities", {})
            if capabilities.get("add"):
                result["warnings"].append(
                    f"Container {container.get('name')} adds capabilities: {capabilities['add']}"
                )
            
            # Check for running as root in container
            if container_sc.get("runAsUser") == 0:
                result["errors"].append(f"Container {container.get('name')} runs as root")
                result["passed"] = False

    async def _validate_service_security(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Service security configuration"""
        spec = config.get("spec", {})
        
        # Check service type
        service_type = spec.get("type", "ClusterIP")
        if service_type == "NodePort":
            result["warnings"].append("NodePort service exposes ports on all nodes")
        elif service_type == "LoadBalancer":
            result["warnings"].append("LoadBalancer service may expose service publicly")
        
        # Check for well-known insecure ports
        insecure_ports = [21, 23, 80, 135, 445, 1433, 3389]
        ports = spec.get("ports", [])
        for port_config in ports:
            port = port_config.get("port")
            if port in insecure_ports:
                result["warnings"].append(f"Service exposes potentially insecure port {port}")

    async def _validate_network_policy_security(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate NetworkPolicy security configuration"""
        spec = config.get("spec", {})
        
        # Check for overly permissive policies
        ingress = spec.get("ingress", [])
        for rule in ingress:
            if not rule.get("from"):
                result["warnings"].append("NetworkPolicy ingress rule allows traffic from anywhere")
        
        egress = spec.get("egress", [])
        for rule in egress:
            if not rule.get("to"):
                result["warnings"].append("NetworkPolicy egress rule allows traffic to anywhere")

    async def _validate_against_security_policies(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate against organizational security policies via MCP"""
        try:
            if self.mcp_broker:
                policies = await self.mcp_broker.invoke_tool(
                    "security_policies",
                    {"policy_type": "all"}
                )
                
                # Example policy checks
                if policies and policies.get("enforcement") == "strict":
                    # Stricter validation in strict mode
                    kind = config.get("kind")
                    if kind == "Deployment":
                        template_spec = config.get("spec", {}).get("template", {}).get("spec", {})
                        if not template_spec.get("securityContext", {}).get("runAsNonRoot"):
                            result["errors"].append("Strict policy requires runAsNonRoot: true")
                            result["passed"] = False
                            
        except Exception as e:
            result["warnings"].append(f"Could not validate against security policies: {str(e)}")

    async def _validate_best_practices(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Level 4: Best practices validation"""
        result = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        kind = config.get("kind")
        
        try:
            if kind == "Deployment":
                await self._validate_deployment_best_practices(config, result)
            elif kind == "Service":
                await self._validate_service_best_practices(config, result)
            
            # General best practices
            await self._validate_general_best_practices(config, result)
                
        except Exception as e:
            result["warnings"].append(f"Best practices validation error: {str(e)}")
        
        return result

    async def _validate_deployment_best_practices(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Deployment best practices"""
        spec = config.get("spec", {})
        template = spec.get("template", {})
        template_spec = template.get("spec", {})
        
        # Check replica count for HA
        replicas = spec.get("replicas", 1)
        if replicas < 2:
            result["recommendations"].append(
                "Consider using at least 2 replicas for high availability"
            )
        
        # Check resource requests and limits
        containers = template_spec.get("containers", [])
        for container in containers:
            resources = container.get("resources", {})
            
            if not resources.get("requests"):
                result["recommendations"].append(
                    f"Container {container.get('name')} should define resource requests"
                )
            
            if not resources.get("limits"):
                result["recommendations"].append(
                    f"Container {container.get('name')} should define resource limits"
                )
            
            # Check for health probes
            if not container.get("livenessProbe"):
                result["recommendations"].append(
                    f"Container {container.get('name')} should define liveness probe"
                )
            
            if not container.get("readinessProbe"):
                result["recommendations"].append(
                    f"Container {container.get('name')} should define readiness probe"
                )
        
        # Check update strategy
        strategy = spec.get("strategy", {})
        if strategy.get("type") == "Recreate":
            result["recommendations"].append(
                "Consider using RollingUpdate strategy for zero-downtime deployments"
            )

    async def _validate_service_best_practices(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate Service best practices"""
        metadata = config.get("metadata", {})
        
        # Check for descriptive labels
        labels = metadata.get("labels", {})
        recommended_labels = ["app", "version", "component"]
        missing_labels = [label for label in recommended_labels if label not in labels]
        
        if missing_labels:
            result["recommendations"].append(
                f"Consider adding recommended labels: {', '.join(missing_labels)}"
            )

    async def _validate_general_best_practices(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Validate general Kubernetes best practices"""
        metadata = config.get("metadata", {})
        
        # Check for namespace
        if not metadata.get("namespace"):
            result["recommendations"].append("Consider specifying a namespace explicitly")
        
        # Check for labels
        labels = metadata.get("labels", {})
        if not labels:
            result["recommendations"].append("Consider adding descriptive labels")
        
        # Check for annotations for documentation
        annotations = metadata.get("annotations", {})
        if not annotations:
            result["recommendations"].append("Consider adding annotations for documentation")

    def _is_valid_dns_name(self, name: str) -> bool:
        """Check if name is a valid DNS subdomain name"""
        import re
        # DNS subdomain name must be lowercase alphanumeric and hyphens
        pattern = r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
        return bool(re.match(pattern, name)) and len(name) <= 63

    async def inject_validation_errors(self, 
                                     configs: List[Dict[str, Any]],
                                     error_types: List[str]) -> List[Dict[str, Any]]:
        """Inject validation errors for testing validation framework effectiveness"""
        modified_configs = []
        
        for i, config in enumerate(configs):
            modified_config = config.copy()
            
            # Inject different types of errors for testing
            if "syntax" in error_types and i % 3 == 0:
                # Remove required field
                if "metadata" in modified_config:
                    del modified_config["metadata"]["name"]
            
            elif "security" in error_types and i % 3 == 1:
                # Make container run as root
                if modified_config.get("kind") == "Deployment":
                    containers = modified_config.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    for container in containers:
                        if "securityContext" not in container:
                            container["securityContext"] = {}
                        container["securityContext"]["runAsUser"] = 0
            
            elif "best_practice" in error_types and i % 3 == 2:
                # Remove resource limits
                if modified_config.get("kind") == "Deployment":
                    containers = modified_config.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    for container in containers:
                        if "resources" in container:
                            del container["resources"]
            
            modified_configs.append(modified_config)
        
        return modified_configs 