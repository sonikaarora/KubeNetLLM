"""
Test Scenarios for KubeNetLLM Experiments.
Contains the 5 experimental scenarios from the research paper.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ScenarioResult:
    """Result from running a test scenario"""
    success: bool
    execution_time: float
    api_calls: int
    tokens_used: int
    validation_result: Dict[str, Any]
    generated_configs: List[Dict[str, Any]]
    deployment_result: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class TestScenarios:
    """
    Test scenarios for KubeNetLLM experiments.
    Implements the 5 experimental scenarios from the research paper.
    """

    def __init__(self, framework):
        """
        Initialize test scenarios.
        
        Args:
            framework: KubeNetLLM framework instance
        """
        self.framework = framework
        self.logger = structlog.get_logger(__name__)

    async def run_simple_web_app(self) -> Dict[str, Any]:
        """
        Scenario 1: Simple Web Application
        
        Tests basic configuration generation for a simple web application
        with frontend, backend, and database components.
        """
        self.logger.info("Running Scenario 1: Simple Web Application")
        
        requirements = """
        Deploy a simple web application with the following requirements:
        - Frontend: nginx web server exposed on port 80
        - Backend: Node.js API service on port 8080  
        - Database: PostgreSQL database with persistent storage
        - All components should have 2 replicas for basic high availability
        - Basic network policies to restrict traffic between tiers
        - Ingress controller to expose the frontend publicly
        - All containers should run as non-root users
        - Resource limits: frontend (500m CPU, 1Gi RAM), backend (1 CPU, 2Gi RAM), database (1.5 CPU, 3Gi RAM)
        """
        
        start_time = time.time()
        
        try:
            # Step 1: Process requirements through NL interface
            processed_requirements = await self.framework.process_requirements(requirements)
            
            # Step 2: Generate configurations
            configurations = await self.framework.generate_configurations(processed_requirements)
            
            # Step 3: Validate configurations
            validation_result = await self.framework.validate_configurations(configurations)
            
            # Step 4: Deploy (dry run)
            deployment_result = await self.framework.deploy_configurations(
                configurations, dry_run=True
            )
            
            execution_time = time.time() - start_time
            
            # Calculate metrics
            api_calls = (self.framework.interface.get_api_call_count() +
                        self.framework.generator.get_api_call_count())
            tokens_used = (self.framework.interface.get_token_usage() +
                          self.framework.generator.get_token_usage())
            
            success = (validation_result.get("overall_valid", False) and
                      deployment_result.get("success", False))
            
            return {
                "success": success,
                "execution_time": execution_time,
                "api_calls": api_calls,
                "tokens_used": tokens_used,
                "validation_result": validation_result,
                "generated_configs": configurations,
                "deployment_result": deployment_result,
                "config_count": len(configurations),
                "mcp_calls": 2  # Cluster info + security policies
            }
            
        except Exception as e:
            self.logger.error("Scenario 1 failed", error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            }

    async def run_microservices(self) -> Dict[str, Any]:
        """
        Scenario 2: Microservices with Service Mesh
        
        Tests complex microservices architecture with Istio service mesh,
        mTLS, traffic management, and circuit breakers.
        """
        self.logger.info("Running Scenario 2: Microservices with Service Mesh")
        
        requirements = """
        Create a microservices architecture with service mesh:
        - Services: user-service, product-service, order-service, payment-service, notification-service
        - Each service needs 3 replicas with different resource requirements
        - Istio service mesh with mTLS enabled between all services
        - Traffic routing: 80% traffic to v1, 20% to v2 for product-service (canary deployment)
        - Circuit breaker pattern for payment-service with 5-second timeout
        - Load balancing: round-robin for user-service, random for others
        - Retry policy: 3 retries with exponential backoff for order-service
        - Service-to-service authentication using JWT tokens
        - Distributed tracing with Jaeger integration
        - Rate limiting: 100 requests per minute per user for user-service
        - All services expose metrics on /metrics endpoint
        """
        
        start_time = time.time()
        
        try:
            # Process requirements
            processed_requirements = await self.framework.process_requirements(requirements)
            
            # Generate configurations
            configurations = await self.framework.generate_configurations(processed_requirements)
            
            # Validate configurations
            validation_result = await self.framework.validate_configurations(configurations)
            
            # Deploy (dry run)
            deployment_result = await self.framework.deploy_configurations(
                configurations, dry_run=True
            )
            
            execution_time = time.time() - start_time
            
            # Calculate metrics
            api_calls = (self.framework.interface.get_api_call_count() +
                        self.framework.generator.get_api_call_count())
            tokens_used = (self.framework.interface.get_token_usage() +
                          self.framework.generator.get_token_usage())
            
            success = (validation_result.get("overall_valid", False) and
                      deployment_result.get("success", False))
            
            return {
                "success": success,
                "execution_time": execution_time,
                "api_calls": api_calls,
                "tokens_used": tokens_used,
                "validation_result": validation_result,
                "generated_configs": configurations,
                "deployment_result": deployment_result,
                "config_count": len(configurations),
                "mcp_calls": 4  # Cluster info + security policies + docs + knowledge base
            }
            
        except Exception as e:
            self.logger.error("Scenario 2 failed", error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            }

    async def run_multi_environment(self) -> Dict[str, Any]:
        """
        Scenario 3: Multi-Environment Configuration
        
        Tests configuration generation for multiple environments
        (development, staging, production) with different requirements.
        """
        self.logger.info("Running Scenario 3: Multi-Environment Configuration")
        
        requirements = """
        Deploy application across three environments with different configurations:
        
        Development Environment:
        - Single replica for all services
        - No resource limits
        - SQLite database (no persistence required)
        - HTTP only (no TLS)
        - Debug logging enabled
        - All services in single namespace: dev
        
        Staging Environment:  
        - 2 replicas for each service
        - Moderate resource limits (0.5 CPU, 1Gi RAM per service)
        - PostgreSQL database with 10Gi storage
        - TLS with self-signed certificates
        - Info level logging
        - Network policies for basic isolation
        - Namespace: staging
        
        Production Environment:
        - 3 replicas minimum, autoscaling up to 10 replicas
        - Strict resource limits and requests
        - PostgreSQL with 100Gi storage and backups
        - TLS with valid certificates from Let's Encrypt
        - Error level logging only
        - Comprehensive network policies and security contexts
        - Pod security policies enforced
        - Monitoring and alerting enabled
        - Namespace: production
        
        Each environment should have its own database connection settings,
        different ingress configurations, and environment-specific secrets.
        """
        
        start_time = time.time()
        
        try:
            # Process requirements
            processed_requirements = await self.framework.process_requirements(requirements)
            
            # Generate configurations
            configurations = await self.framework.generate_configurations(processed_requirements)
            
            # Validate configurations
            validation_result = await self.framework.validate_configurations(configurations)
            
            # Deploy (dry run)
            deployment_result = await self.framework.deploy_configurations(
                configurations, dry_run=True
            )
            
            execution_time = time.time() - start_time
            
            # Calculate metrics
            api_calls = (self.framework.interface.get_api_call_count() +
                        self.framework.generator.get_api_call_count())
            tokens_used = (self.framework.interface.get_token_usage() +
                          self.framework.generator.get_token_usage())
            
            success = (validation_result.get("overall_valid", False) and
                      deployment_result.get("success", False))
            
            return {
                "success": success,
                "execution_time": execution_time,
                "api_calls": api_calls,
                "tokens_used": tokens_used,
                "validation_result": validation_result,
                "generated_configs": configurations,
                "deployment_result": deployment_result,
                "config_count": len(configurations),
                "mcp_calls": 3  # Cluster info + security policies + knowledge base
            }
            
        except Exception as e:
            self.logger.error("Scenario 3 failed", error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            }

    async def run_security_focused(self) -> Dict[str, Any]:
        """
        Scenario 4: Security-Focused Deployment
        
        Tests generation of highly secure configurations with comprehensive
        security policies and compliance requirements.
        """
        self.logger.info("Running Scenario 4: Security-Focused Deployment")
        
        requirements = """
        Deploy a highly secure financial application with strict security requirements:
        
        Security Requirements:
        - Zero-trust networking: deny all traffic by default
        - mTLS for all service-to-service communication
        - Pod Security Standards: restricted profile enforced
        - All containers must run as non-root users (UID > 1000)
        - Read-only root filesystem for all containers
        - No privilege escalation allowed
        - Drop all capabilities except NET_BIND_SERVICE if needed
        - Network policies: explicit allow rules only
        - Secrets management: external secrets operator integration
        - Image scanning: only signed images from approved registries
        - RBAC: least privilege principle with service accounts
        - Audit logging: all API calls logged
        - Encryption at rest for all persistent volumes
        - Runtime security: Falco integration for anomaly detection
        - Compliance: SOC2 and PCI-DSS requirements
        
        Application Components:
        - Frontend: React application (nginx) - 2 replicas
        - API Gateway: Express.js - 3 replicas  
        - Auth Service: OAuth2/JWT - 2 replicas
        - Transaction Service: Core business logic - 3 replicas
        - Database: PostgreSQL with encryption - 1 replica
        - Cache: Redis with TLS - 2 replicas
        - Message Queue: RabbitMQ with TLS - 2 replicas
        
        All components need health checks, resource limits, and security contexts.
        Database credentials must be rotated every 30 days.
        """
        
        start_time = time.time()
        
        try:
            # Process requirements
            processed_requirements = await self.framework.process_requirements(requirements)
            
            # Generate configurations
            configurations = await self.framework.generate_configurations(processed_requirements)
            
            # Validate configurations
            validation_result = await self.framework.validate_configurations(configurations)
            
            # Deploy (dry run)
            deployment_result = await self.framework.deploy_configurations(
                configurations, dry_run=True
            )
            
            execution_time = time.time() - start_time
            
            # Calculate metrics
            api_calls = (self.framework.interface.get_api_call_count() +
                        self.framework.generator.get_api_call_count())
            tokens_used = (self.framework.interface.get_token_usage() +
                          self.framework.generator.get_token_usage())
            
            success = (validation_result.get("overall_valid", False) and
                      deployment_result.get("success", False))
            
            return {
                "success": success,
                "execution_time": execution_time,
                "api_calls": api_calls,
                "tokens_used": tokens_used,
                "validation_result": validation_result,
                "generated_configs": configurations,
                "deployment_result": deployment_result,
                "config_count": len(configurations),
                "mcp_calls": 5  # Cluster info + security policies + docs + knowledge base + config validator
            }
            
        except Exception as e:
            self.logger.error("Scenario 4 failed", error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            }

    async def run_edge_cases(self) -> Dict[str, Any]:
        """
        Scenario 5: Edge Case Handling
        
        Tests framework's ability to handle ambiguous, incomplete,
        or conflicting requirements gracefully.
        """
        self.logger.info("Running Scenario 5: Edge Case Handling")
        
        # Test with intentionally ambiguous requirements
        requirements = """
        I need a highly available application that performs really well
        and is very secure. It should handle lots of users and be scalable.
        The application needs to store data and should work in the cloud.
        It should be easy to update and maintain. Also, it needs to be
        cost-effective and follow best practices.
        """
        
        start_time = time.time()
        
        try:
            # Process requirements
            processed_requirements = await self.framework.process_requirements(requirements)
            
            # Generate configurations
            configurations = await self.framework.generate_configurations(processed_requirements)
            
            # Validate configurations
            validation_result = await self.framework.validate_configurations(configurations)
            
            # Deploy (dry run)
            deployment_result = await self.framework.deploy_configurations(
                configurations, dry_run=True
            )
            
            execution_time = time.time() - start_time
            
            # Calculate metrics
            api_calls = (self.framework.interface.get_api_call_count() +
                        self.framework.generator.get_api_call_count())
            tokens_used = (self.framework.interface.get_token_usage() +
                          self.framework.generator.get_token_usage())
            
            # For edge cases, we expect some issues but framework should handle gracefully
            success = (len(configurations) > 0 and
                      validation_result.get("summary", {}).get("total_recommendations", 0) > 0)
            
            return {
                "success": success,
                "execution_time": execution_time,
                "api_calls": api_calls,
                "tokens_used": tokens_used,
                "validation_result": validation_result,
                "generated_configs": configurations,
                "deployment_result": deployment_result,
                "config_count": len(configurations),
                "mcp_calls": 2,  # Cluster info + knowledge base
                "edge_case_handling": {
                    "ambiguous_requirements": True,
                    "clarifications_needed": len(processed_requirements.clarifications) if hasattr(processed_requirements, 'clarifications') else 0,
                    "assumptions_made": len(processed_requirements.assumptions) if hasattr(processed_requirements, 'assumptions') else 0,
                    "default_values_used": True
                }
            }
            
        except Exception as e:
            self.logger.error("Scenario 5 failed", error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            }

    async def run_custom_scenario(self, requirements: str, scenario_name: str) -> Dict[str, Any]:
        """
        Run a custom scenario with user-provided requirements.
        
        Args:
            requirements: Natural language requirements
            scenario_name: Name for the scenario
            
        Returns:
            Scenario results
        """
        self.logger.info("Running custom scenario", scenario=scenario_name)
        
        start_time = time.time()
        
        try:
            # Process requirements
            processed_requirements = await self.framework.process_requirements(requirements)
            
            # Generate configurations
            configurations = await self.framework.generate_configurations(processed_requirements)
            
            # Validate configurations
            validation_result = await self.framework.validate_configurations(configurations)
            
            # Deploy (dry run)
            deployment_result = await self.framework.deploy_configurations(
                configurations, dry_run=True
            )
            
            execution_time = time.time() - start_time
            
            # Calculate metrics
            api_calls = (self.framework.interface.get_api_call_count() +
                        self.framework.generator.get_api_call_count())
            tokens_used = (self.framework.interface.get_token_usage() +
                          self.framework.generator.get_token_usage())
            
            success = (validation_result.get("overall_valid", False) and
                      deployment_result.get("success", False))
            
            return {
                "success": success,
                "execution_time": execution_time,
                "api_calls": api_calls,
                "tokens_used": tokens_used,
                "validation_result": validation_result,
                "generated_configs": configurations,
                "deployment_result": deployment_result,
                "config_count": len(configurations),
                "mcp_calls": 2,
                "scenario_name": scenario_name
            }
            
        except Exception as e:
            self.logger.error("Custom scenario failed", scenario=scenario_name, error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            }

    async def run_validation_stress_test(self) -> Dict[str, Any]:
        """
        Run a stress test to evaluate validation framework effectiveness.
        Generates configurations with intentional errors to test error detection.
        """
        self.logger.info("Running validation stress test")
        
        start_time = time.time()
        
        try:
            # Generate configurations with known issues
            problematic_configs = [
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {
                        # Missing required name field
                        "namespace": "default"
                    },
                    "spec": {
                        "replicas": 1,
                        "selector": {"matchLabels": {"app": "test"}},
                        "template": {
                            "metadata": {"labels": {"app": "test"}},
                            "spec": {
                                "containers": [{
                                    "name": "test",
                                    "image": "nginx:latest",  # Using latest tag
                                    "securityContext": {
                                        "runAsUser": 0  # Running as root
                                    }
                                }]
                            }
                        }
                    }
                },
                {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {
                        "name": "test-service",
                        "namespace": "default"
                    },
                    "spec": {
                        "selector": {"app": "nonexistent"},  # Selector doesn't match any deployment
                        "ports": [
                            {"port": 80, "targetPort": 80},
                            {"port": 80, "targetPort": 8080}  # Duplicate port
                        ]
                    }
                }
            ]
            
            # Run validation
            validation_result = await self.framework.validate_configurations(problematic_configs)
            
            execution_time = time.time() - start_time
            
            # Check if validation caught the issues
            total_issues = (validation_result.get("summary", {}).get("total_errors", 0) +
                           validation_result.get("summary", {}).get("total_warnings", 0))
            
            detection_rate = (total_issues / 4) * 100  # We injected 4 issues
            
            return {
                "success": True,
                "execution_time": execution_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": validation_result,
                "generated_configs": problematic_configs,
                "config_count": len(problematic_configs),
                "detection_rate": detection_rate,
                "issues_detected": total_issues,
                "issues_injected": 4
            }
            
        except Exception as e:
            self.logger.error("Validation stress test failed", error=str(e))
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "api_calls": 0,
                "tokens_used": 0,
                "validation_result": {},
                "generated_configs": [],
                "errors": [str(e)]
            } 