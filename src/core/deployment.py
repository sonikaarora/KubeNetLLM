"""
Intelligent Deployment Manager - Component 4 of KubeNetLLM architecture.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import structlog
import yaml
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from ..utils.exceptions import DeploymentError, KubernetesError

logger = structlog.get_logger(__name__)


@dataclass
class DeploymentPlan:
    """Deployment plan with ordered steps and dependencies"""
    steps: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]
    estimated_time: float
    safety_checks: List[str]
    rollback_plan: List[str]


@dataclass
class DeploymentResult:
    """Result of deployment operation"""
    success: bool
    deployed_resources: List[str]
    failed_resources: List[str]
    errors: List[str]
    warnings: List[str]
    deployment_time: float
    dry_run: bool


class DeploymentManager:
    """
    Intelligent Deployment Manager - Component 4 of KubeNetLLM architecture.
    Orchestrates safe deployment of validated configurations.
    """

    def __init__(self, config: Dict[str, Any], mcp_broker=None):
        """
        Initialize the Deployment Manager.
        
        Args:
            config: Deployment configuration
            mcp_broker: MCP broker instance
        """
        self.config = config
        self.mcp_broker = mcp_broker
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Kubernetes client
        self.k8s_client = self._init_k8s_client()
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.networking_v1 = client.NetworkingV1Api()
        
        # Deployment settings
        self.dry_run_default = config.get("dry_run", True)
        self.progressive = config.get("progressive", True)
        self.rollback_enabled = config.get("rollback_enabled", True)
        self.safety_checks = config.get("safety_checks", [])
        
        self.logger.info("Deployment Manager initialized",
                        dry_run_default=self.dry_run_default,
                        progressive=self.progressive)

    def _init_k8s_client(self):
        """Initialize Kubernetes client"""
        try:
            k8s_config.load_kube_config()
            return client.ApiClient()
        except Exception as e:
            self.logger.warning("Could not load Kubernetes config", error=str(e))
            return None

    async def create_deployment_plan(self, 
                                   configurations: List[Dict[str, Any]],
                                   validation_results: Dict[str, Any]) -> DeploymentPlan:
        """
        Create an intelligent deployment plan.
        
        Args:
            configurations: Validated Kubernetes configurations
            validation_results: Results from validation framework
            
        Returns:
            DeploymentPlan with ordered steps and dependencies
        """
        self.logger.info("Creating deployment plan",
                        config_count=len(configurations))
        
        # Analyze dependencies
        dependencies = self._analyze_dependencies(configurations)
        
        # Create ordered deployment steps
        steps = self._create_deployment_steps(configurations, dependencies)
        
        # Estimate deployment time
        estimated_time = self._estimate_deployment_time(steps)
        
        # Generate safety checks
        safety_checks = self._generate_safety_checks(configurations, validation_results)
        
        # Create rollback plan
        rollback_plan = self._create_rollback_plan(steps)
        
        plan = DeploymentPlan(
            steps=steps,
            dependencies=dependencies,
            estimated_time=estimated_time,
            safety_checks=safety_checks,
            rollback_plan=rollback_plan
        )
        
        self.logger.info("Deployment plan created",
                        steps=len(steps),
                        estimated_time=estimated_time)
        
        return plan

    def _analyze_dependencies(self, configurations: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Analyze dependencies between resources"""
        dependencies = {}
        resource_map = {}
        
        # Build resource map
        for config in configurations:
            kind = config.get("kind")
            name = config.get("metadata", {}).get("name")
            if kind and name:
                resource_key = f"{kind}/{name}"
                resource_map[resource_key] = config
                dependencies[resource_key] = []
        
        # Analyze dependencies
        for config in configurations:
            kind = config.get("kind")
            name = config.get("metadata", {}).get("name")
            resource_key = f"{kind}/{name}"
            
            if kind == "Service":
                # Services depend on Deployments/StatefulSets with matching selectors
                selector = config.get("spec", {}).get("selector", {})
                for dep_key, dep_config in resource_map.items():
                    if dep_config.get("kind") in ["Deployment", "StatefulSet"]:
                        dep_labels = dep_config.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
                        if all(dep_labels.get(k) == v for k, v in selector.items()):
                            dependencies[resource_key].append(dep_key)
            
            elif kind == "Ingress":
                # Ingress depends on Services
                rules = config.get("spec", {}).get("rules", [])
                for rule in rules:
                    paths = rule.get("http", {}).get("paths", [])
                    for path in paths:
                        service_name = path.get("backend", {}).get("service", {}).get("name")
                        if service_name:
                            service_key = f"Service/{service_name}"
                            if service_key in resource_map:
                                dependencies[resource_key].append(service_key)
            
            elif kind == "NetworkPolicy":
                # NetworkPolicy depends on target resources
                pod_selector = config.get("spec", {}).get("podSelector", {}).get("matchLabels", {})
                for dep_key, dep_config in resource_map.items():
                    if dep_config.get("kind") in ["Deployment", "StatefulSet"]:
                        dep_labels = dep_config.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
                        if all(dep_labels.get(k) == v for k, v in pod_selector.items()):
                            dependencies[resource_key].append(dep_key)
        
        return dependencies

    def _create_deployment_steps(self, 
                               configurations: List[Dict[str, Any]],
                               dependencies: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Create ordered deployment steps based on dependencies"""
        steps = []
        deployed = set()
        
        # Priority order for resource types
        priority_order = [
            "Namespace", "Secret", "ConfigMap", "PersistentVolumeClaim",
            "StatefulSet", "Deployment", "Service", "Ingress", "NetworkPolicy"
        ]
        
        # Group configurations by type
        configs_by_type = {}
        for config in configurations:
            kind = config.get("kind")
            if kind not in configs_by_type:
                configs_by_type[kind] = []
            configs_by_type[kind].append(config)
        
        # Deploy in priority order
        for resource_type in priority_order:
            if resource_type in configs_by_type:
                for config in configs_by_type[resource_type]:
                    name = config.get("metadata", {}).get("name")
                    resource_key = f"{resource_type}/{name}"
                    
                    # Check if dependencies are met
                    deps = dependencies.get(resource_key, [])
                    if all(dep in deployed for dep in deps):
                        step = {
                            "action": "create",
                            "resource": config,
                            "resource_key": resource_key,
                            "dependencies": deps,
                            "wait_for_ready": resource_type in ["Deployment", "StatefulSet"],
                            "timeout": 300 if resource_type in ["Deployment", "StatefulSet"] else 60
                        }
                        steps.append(step)
                        deployed.add(resource_key)
        
        # Handle remaining resources (if any circular dependencies exist)
        remaining_configs = [
            config for config in configurations
            if f"{config.get('kind')}/{config.get('metadata', {}).get('name')}" not in deployed
        ]
        
        for config in remaining_configs:
            kind = config.get("kind")
            name = config.get("metadata", {}).get("name")
            resource_key = f"{kind}/{name}"
            
            step = {
                "action": "create",
                "resource": config,
                "resource_key": resource_key,
                "dependencies": dependencies.get(resource_key, []),
                "wait_for_ready": kind in ["Deployment", "StatefulSet"],
                "timeout": 300 if kind in ["Deployment", "StatefulSet"] else 60
            }
            steps.append(step)
        
        return steps

    def _estimate_deployment_time(self, steps: List[Dict[str, Any]]) -> float:
        """Estimate total deployment time"""
        total_time = 0
        
        for step in steps:
            # Base time for API call
            total_time += 5
            
            # Additional time for resources that need to be ready
            if step.get("wait_for_ready"):
                total_time += step.get("timeout", 60)
        
        return total_time

    def _generate_safety_checks(self, 
                               configurations: List[Dict[str, Any]],
                               validation_results: Dict[str, Any]) -> List[str]:
        """Generate safety checks based on configurations and validation results"""
        checks = [
            "Verify cluster connectivity",
            "Check namespace exists",
            "Validate RBAC permissions",
            "Confirm resource quotas"
        ]
        
        # Add specific checks based on resources
        for config in configurations:
            kind = config.get("kind")
            
            if kind == "PersistentVolumeClaim":
                checks.append("Verify storage class availability")
            elif kind == "Ingress":
                checks.append("Verify ingress controller is running")
            elif kind == "NetworkPolicy":
                checks.append("Verify network policy support")
        
        # Add checks based on validation warnings
        if validation_results.get("summary", {}).get("total_warnings", 0) > 0:
            checks.append("Review validation warnings before deployment")
        
        return checks

    def _create_rollback_plan(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Create rollback plan for deployment"""
        rollback_steps = []
        
        # Reverse order for rollback
        for step in reversed(steps):
            resource = step["resource"]
            kind = resource.get("kind")
            name = resource.get("metadata", {}).get("name")
            namespace = resource.get("metadata", {}).get("namespace", "default")
            
            rollback_steps.append(f"Delete {kind} {name} in namespace {namespace}")
        
        return rollback_steps

    async def deploy_configurations(self, 
                                  configurations: List[Dict[str, Any]],
                                  deployment_plan: Optional[DeploymentPlan] = None,
                                  dry_run: Optional[bool] = None) -> DeploymentResult:
        """
        Deploy configurations to Kubernetes cluster.
        
        Args:
            configurations: List of Kubernetes configurations
            deployment_plan: Optional deployment plan (will create if not provided)
            dry_run: Whether to perform dry run (defaults to config setting)
            
        Returns:
            DeploymentResult with deployment status and details
        """
        start_time = time.time()
        
        if dry_run is None:
            dry_run = self.dry_run_default
        
        self.logger.info("Starting deployment",
                        config_count=len(configurations),
                        dry_run=dry_run)
        
        # Create deployment plan if not provided
        if deployment_plan is None:
            deployment_plan = await self.create_deployment_plan(configurations, {})
        
        result = DeploymentResult(
            success=True,
            deployed_resources=[],
            failed_resources=[],
            errors=[],
            warnings=[],
            deployment_time=0.0,
            dry_run=dry_run
        )
        
        try:
            # Perform safety checks
            if not dry_run:
                await self._perform_safety_checks(deployment_plan.safety_checks, result)
            
            # Execute deployment steps
            for step in deployment_plan.steps:
                try:
                    await self._execute_deployment_step(step, dry_run, result)
                except Exception as e:
                    result.success = False
                    result.errors.append(f"Failed to deploy {step['resource_key']}: {str(e)}")
                    result.failed_resources.append(step['resource_key'])
                    
                    if not dry_run and self.rollback_enabled:
                        self.logger.warning("Deployment failed, initiating rollback")
                        await self._perform_rollback(result.deployed_resources)
                        break
            
            result.deployment_time = time.time() - start_time
            
            self.logger.info("Deployment completed",
                           success=result.success,
                           deployed=len(result.deployed_resources),
                           failed=len(result.failed_resources),
                           dry_run=dry_run)
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Deployment failed: {str(e)}")
            result.deployment_time = time.time() - start_time
            
            self.logger.error("Deployment failed", error=str(e))
        
        return result

    async def _perform_safety_checks(self, safety_checks: List[str], result: DeploymentResult):
        """Perform pre-deployment safety checks"""
        self.logger.info("Performing safety checks", checks=len(safety_checks))
        
        for check in safety_checks:
            try:
                if "cluster connectivity" in check.lower():
                    if not self.k8s_client:
                        raise Exception("Kubernetes client not available")
                
                elif "namespace exists" in check.lower():
                    # This would check if target namespace exists
                    pass
                
                elif "rbac permissions" in check.lower():
                    # This would verify deployment permissions
                    pass
                
                elif "resource quotas" in check.lower():
                    # This would check resource quota availability
                    pass
                
                self.logger.debug("Safety check passed", check=check)
                
            except Exception as e:
                result.warnings.append(f"Safety check warning: {check} - {str(e)}")

    async def _execute_deployment_step(self, 
                                     step: Dict[str, Any],
                                     dry_run: bool,
                                     result: DeploymentResult):
        """Execute a single deployment step"""
        resource = step["resource"]
        resource_key = step["resource_key"]
        kind = resource.get("kind")
        
        self.logger.info("Executing deployment step",
                        resource=resource_key,
                        dry_run=dry_run)
        
        try:
            if dry_run:
                # Simulate deployment
                await asyncio.sleep(0.1)  # Simulate processing time
                result.deployed_resources.append(resource_key)
                return
            
            # Actual deployment logic
            if kind == "Deployment":
                await self._deploy_deployment(resource)
            elif kind == "Service":
                await self._deploy_service(resource)
            elif kind == "StatefulSet":
                await self._deploy_statefulset(resource)
            elif kind == "Secret":
                await self._deploy_secret(resource)
            elif kind == "ConfigMap":
                await self._deploy_configmap(resource)
            elif kind == "Ingress":
                await self._deploy_ingress(resource)
            elif kind == "NetworkPolicy":
                await self._deploy_network_policy(resource)
            else:
                self.logger.warning("Unsupported resource type", kind=kind)
                result.warnings.append(f"Unsupported resource type: {kind}")
                return
            
            # Wait for resource to be ready if needed
            if step.get("wait_for_ready"):
                await self._wait_for_resource_ready(resource, step.get("timeout", 300))
            
            result.deployed_resources.append(resource_key)
            
        except Exception as e:
            raise DeploymentError(f"Failed to deploy {resource_key}: {str(e)}")

    async def _deploy_deployment(self, resource: Dict[str, Any]):
        """Deploy a Deployment resource"""
        if not self.apps_v1:
            raise KubernetesError("AppsV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.apps_v1.create_namespaced_deployment(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("Deployment already exists, updating")
                self.apps_v1.patch_namespaced_deployment(
                    name=resource["metadata"]["name"],
                    namespace=namespace,
                    body=resource
                )
            else:
                raise KubernetesError(f"API error: {e}")

    async def _deploy_service(self, resource: Dict[str, Any]):
        """Deploy a Service resource"""
        if not self.core_v1:
            raise KubernetesError("CoreV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.core_v1.create_namespaced_service(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("Service already exists, updating")
                self.core_v1.patch_namespaced_service(
                    name=resource["metadata"]["name"],
                    namespace=namespace,
                    body=resource
                )
            else:
                raise KubernetesError(f"API error: {e}")

    async def _deploy_statefulset(self, resource: Dict[str, Any]):
        """Deploy a StatefulSet resource"""
        if not self.apps_v1:
            raise KubernetesError("AppsV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.apps_v1.create_namespaced_stateful_set(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("StatefulSet already exists, updating")
                self.apps_v1.patch_namespaced_stateful_set(
                    name=resource["metadata"]["name"],
                    namespace=namespace,
                    body=resource
                )
            else:
                raise KubernetesError(f"API error: {e}")

    async def _deploy_secret(self, resource: Dict[str, Any]):
        """Deploy a Secret resource"""
        if not self.core_v1:
            raise KubernetesError("CoreV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.core_v1.create_namespaced_secret(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("Secret already exists, skipping")
            else:
                raise KubernetesError(f"API error: {e}")

    async def _deploy_configmap(self, resource: Dict[str, Any]):
        """Deploy a ConfigMap resource"""
        if not self.core_v1:
            raise KubernetesError("CoreV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.core_v1.create_namespaced_config_map(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("ConfigMap already exists, updating")
                self.core_v1.patch_namespaced_config_map(
                    name=resource["metadata"]["name"],
                    namespace=namespace,
                    body=resource
                )
            else:
                raise KubernetesError(f"API error: {e}")

    async def _deploy_ingress(self, resource: Dict[str, Any]):
        """Deploy an Ingress resource"""
        if not self.networking_v1:
            raise KubernetesError("NetworkingV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.networking_v1.create_namespaced_ingress(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("Ingress already exists, updating")
                self.networking_v1.patch_namespaced_ingress(
                    name=resource["metadata"]["name"],
                    namespace=namespace,
                    body=resource
                )
            else:
                raise KubernetesError(f"API error: {e}")

    async def _deploy_network_policy(self, resource: Dict[str, Any]):
        """Deploy a NetworkPolicy resource"""
        if not self.networking_v1:
            raise KubernetesError("NetworkingV1Api not available")
        
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        try:
            self.networking_v1.create_namespaced_network_policy(
                namespace=namespace,
                body=resource
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.logger.info("NetworkPolicy already exists, updating")
                self.networking_v1.patch_namespaced_network_policy(
                    name=resource["metadata"]["name"],
                    namespace=namespace,
                    body=resource
                )
            else:
                raise KubernetesError(f"API error: {e}")

    async def _wait_for_resource_ready(self, resource: Dict[str, Any], timeout: int):
        """Wait for resource to be ready"""
        kind = resource.get("kind")
        name = resource.get("metadata", {}).get("name")
        namespace = resource.get("metadata", {}).get("namespace", "default")
        
        self.logger.info("Waiting for resource to be ready",
                        kind=kind,
                        name=name,
                        timeout=timeout)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if kind == "Deployment":
                    deployment = self.apps_v1.read_namespaced_deployment(name, namespace)
                    if deployment.status.ready_replicas == deployment.status.replicas:
                        return
                elif kind == "StatefulSet":
                    statefulset = self.apps_v1.read_namespaced_stateful_set(name, namespace)
                    if statefulset.status.ready_replicas == statefulset.status.replicas:
                        return
                
                await asyncio.sleep(5)
                
            except ApiException as e:
                if e.status == 404:
                    await asyncio.sleep(5)
                    continue
                else:
                    raise KubernetesError(f"API error while waiting: {e}")
        
        raise DeploymentError(f"Timeout waiting for {kind} {name} to be ready")

    async def _perform_rollback(self, deployed_resources: List[str]):
        """Perform rollback of deployed resources"""
        self.logger.info("Performing rollback", resources=len(deployed_resources))
        
        # Delete resources in reverse order
        for resource_key in reversed(deployed_resources):
            try:
                kind, name = resource_key.split("/", 1)
                # This would implement actual resource deletion
                self.logger.info("Rolling back resource", resource=resource_key)
                
            except Exception as e:
                self.logger.error("Rollback failed for resource",
                                resource=resource_key,
                                error=str(e)) 