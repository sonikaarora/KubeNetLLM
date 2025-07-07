"""
KubeNetLLM Framework - Main orchestration class for the four-component architecture.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import structlog
import yaml
from pydantic import BaseModel, Field

from .interface import NaturalLanguageInterface
from .generator import ConfigurationGenerator
from .validation import ValidationFramework
from .deployment import DeploymentManager
from ..mcp.broker import MCPBroker
from ..utils.config import ConfigManager
from ..utils.metrics import MetricsCollector
from ..utils.exceptions import KubeNetLLMException

logger = structlog.get_logger(__name__)


@dataclass
class GenerationRequest:
    """Request for configuration generation"""
    id: str
    natural_language_input: str
    context: Dict[str, Any] = field(default_factory=dict)
    requirements: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GenerationResult:
    """Result of configuration generation"""
    request_id: str
    success: bool
    configurations: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    deployment_plan: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    generation_time: float = 0.0


class KubeNetLLMFramework:
    """
    Main KubeNetLLM Framework orchestrating the four-component architecture:
    1. Natural Language Interface Engine
    2. Configuration Generator with MCP Integration
    3. Hierarchical Validation Framework
    4. Intelligent Deployment Manager
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the KubeNetLLM framework.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = ConfigManager(config_path)
        self.logger = structlog.get_logger(__name__)
        self.metrics = MetricsCollector()
        
        # Initialize components
        self.mcp_broker: Optional[MCPBroker] = None
        self.nl_interface: Optional[NaturalLanguageInterface] = None
        self.config_generator: Optional[ConfigurationGenerator] = None
        self.validation_framework: Optional[ValidationFramework] = None
        self.deployment_manager: Optional[DeploymentManager] = None
        
        # State tracking
        self.is_initialized = False
        self.active_requests: Dict[str, GenerationRequest] = {}
        
        self.logger.info("KubeNetLLM Framework initialized", 
                        config_path=config_path)

    async def initialize(self) -> None:
        """Initialize all framework components"""
        if self.is_initialized:
            self.logger.warning("Framework already initialized")
            return
            
        try:
            self.logger.info("Initializing KubeNetLLM components...")
            
            # Initialize MCP broker first
            self.mcp_broker = MCPBroker(self.config.get("mcp", {}))
            await self.mcp_broker.start()
            
            # Initialize other components
            self.nl_interface = NaturalLanguageInterface(
                config=self.config.get("llm", {}),
                mcp_broker=self.mcp_broker
            )
            
            self.config_generator = ConfigurationGenerator(
                config=self.config.get("llm", {}),
                mcp_broker=self.mcp_broker
            )
            
            self.validation_framework = ValidationFramework(
                config=self.config.get("validation", {}),
                mcp_broker=self.mcp_broker
            )
            
            self.deployment_manager = DeploymentManager(
                config=self.config.get("deployment", {}),
                mcp_broker=self.mcp_broker
            )
            
            self.is_initialized = True
            self.logger.info("KubeNetLLM Framework initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize framework", error=str(e))
            raise KubeNetLLMException(f"Framework initialization failed: {e}")

    async def generate_configuration(self, 
                                   natural_language_input: str,
                                   context: Optional[Dict[str, Any]] = None,
                                   user_id: Optional[str] = None) -> GenerationResult:
        """
        Generate Kubernetes configuration from natural language input.
        
        Args:
            natural_language_input: Natural language description of requirements
            context: Additional context for generation
            user_id: User identifier for tracking
            
        Returns:
            GenerationResult with configurations and validation results
        """
        start_time = time.time()
        
        # Create request
        request = GenerationRequest(
            id=f"req_{int(time.time() * 1000)}",
            natural_language_input=natural_language_input,
            context=context or {},
            user_id=user_id
        )
        
        self.active_requests[request.id] = request
        
        result = GenerationResult(
            request_id=request.id,
            success=False
        )
        
        try:
            self.logger.info("Starting configuration generation",
                           request_id=request.id,
                           user_id=user_id)
            
            # Step 1: Process natural language input
            self.logger.info("Processing natural language input", 
                           request_id=request.id)
            
            processed_requirements = await self.nl_interface.process_input(
                natural_language_input,
                context=request.context
            )
            
            # Step 2: Generate configurations
            self.logger.info("Generating configurations", 
                           request_id=request.id)
            
            configurations = await self.config_generator.generate_configurations(
                requirements=processed_requirements,
                context=request.context
            )
            
            # Step 3: Validate configurations
            self.logger.info("Validating configurations", 
                           request_id=request.id)
            
            validation_results = await self.validation_framework.validate_configurations(
                configurations=configurations,
                requirements=processed_requirements
            )
            
            # Step 4: Create deployment plan
            self.logger.info("Creating deployment plan", 
                           request_id=request.id)
            
            deployment_plan = await self.deployment_manager.create_deployment_plan(
                configurations=configurations,
                validation_results=validation_results
            )
            
            # Calculate metrics
            generation_time = time.time() - start_time
            
            # Collect metrics
            metrics = {
                "generation_time": generation_time,
                "api_calls": (self.nl_interface.get_api_call_count() +
                            self.config_generator.get_api_call_count()),
                "tokens_used": (self.nl_interface.get_token_usage() +
                              self.config_generator.get_token_usage()),
                "validation_pass_rate": validation_results.get("pass_rate", 0),
                "config_count": len(configurations)
            }
            
            # Update result
            result.success = validation_results.get("overall_valid", False)
            result.configurations = configurations
            result.validation_results = validation_results
            result.deployment_plan = deployment_plan
            result.metrics = metrics
            result.generation_time = generation_time
            
            self.logger.info("Configuration generation completed successfully",
                           request_id=request.id,
                           generation_time=generation_time,
                           config_count=len(configurations))
            
        except Exception as e:
            self.logger.error("Configuration generation failed",
                            request_id=request.id,
                            error=str(e))
            
            result.success = False
            result.errors.append(str(e))
            result.generation_time = time.time() - start_time
            
        finally:
            # Clean up
            if request.id in self.active_requests:
                del self.active_requests[request.id]
        
        return result
    
    # Alias methods for compatibility with experiment runner
    async def process_requirements(self, natural_language_input: str) -> Any:
        """Process natural language requirements - alias for experiment compatibility"""
        return await self.nl_interface.process_input(natural_language_input)
    
    async def generate_configurations(self, processed_requirements: Any) -> List[Dict[str, Any]]:
        """Generate configurations from processed requirements - alias for experiment compatibility"""
        return await self.config_generator.generate_configurations(processed_requirements)
    
    async def validate_configurations(self, configurations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate configurations - alias for experiment compatibility"""
        return await self.validation_framework.validate_configurations(configurations)
    
    async def deploy_configurations(self, configurations: List[Dict[str, Any]], dry_run: bool = True) -> Dict[str, Any]:
        """Deploy configurations - alias for experiment compatibility"""
        validation_results = await self.validation_framework.validate_configurations(configurations)
        deployment_plan = await self.deployment_manager.create_deployment_plan(configurations, validation_results)
        return await self.deployment_manager.deploy_configurations(configurations, deployment_plan, dry_run)
    
    # Component access for experiments
    @property
    def interface(self) -> NaturalLanguageInterface:
        """Get natural language interface component"""
        return self.nl_interface
    
    @property
    def generator(self) -> ConfigurationGenerator:
        """Get configuration generator component"""
        return self.config_generator
    
    @property
    def validator(self) -> ValidationFramework:
        """Get validation framework component"""
        return self.validation_framework
    
    @property
    def deployer(self) -> DeploymentManager:
        """Get deployment manager component"""
        return self.deployment_manager

    async def deploy_configuration(self,
                                 generation_result: GenerationResult,
                                 dry_run: bool = True) -> Dict[str, Any]:
        """
        Deploy generated configuration to Kubernetes cluster.
        
        Args:
            generation_result: Result from generate_configuration
            dry_run: Whether to perform dry run deployment
            
        Returns:
            Deployment result with status and details
        """
        if not generation_result.success:
            raise KubeNetLLMException("Cannot deploy failed configuration generation")
            
        self.logger.info("Starting deployment",
                        request_id=generation_result.request_id,
                        dry_run=dry_run)
        
        deployment_result = await self.deployment_manager.deploy_configurations(
            configurations=generation_result.configurations,
            deployment_plan=generation_result.deployment_plan,
            dry_run=dry_run
        )
        
        self.logger.info("Deployment completed",
                        request_id=generation_result.request_id,
                        success=deployment_result.get("success", False))
        
        return deployment_result

    async def validate_existing_configuration(self,
                                           configuration_path: str) -> Dict[str, Any]:
        """
        Validate existing Kubernetes configuration files.
        
        Args:
            configuration_path: Path to configuration file or directory
            
        Returns:
            Validation results
        """
        self.logger.info("Validating existing configuration",
                        path=configuration_path)
        
        # Load configurations
        configurations = []
        with open(configuration_path, 'r') as f:
            if configuration_path.endswith('.yaml') or configuration_path.endswith('.yml'):
                configs = yaml.safe_load_all(f)
                configurations.extend(configs)
            else:
                raise KubeNetLLMException(f"Unsupported file type: {configuration_path}")
        
        # Validate
        validation_results = await self.validation_framework.validate_configurations(
            configurations=configurations,
            requirements={}
        )
        
        return validation_results

    async def get_metrics(self) -> Dict[str, Any]:
        """Get framework metrics"""
        return {
            "active_requests": len(self.active_requests),
            "is_initialized": self.is_initialized,
            "component_status": {
                "mcp_broker": self.mcp_broker.is_running if self.mcp_broker else False,
                "nl_interface": self.nl_interface is not None,
                "config_generator": self.config_generator is not None,
                "validation_framework": self.validation_framework is not None,
                "deployment_manager": self.deployment_manager is not None,
            },
            "metrics": self.metrics.get_all_metrics()
        }

    async def shutdown(self) -> None:
        """Shutdown the framework and clean up resources"""
        self.logger.info("Shutting down KubeNetLLM Framework")
        
        # Stop MCP broker
        if self.mcp_broker:
            await self.mcp_broker.stop()
            
        # Clear active requests
        self.active_requests.clear()
        
        self.is_initialized = False
        self.logger.info("KubeNetLLM Framework shutdown complete")


# Convenience functions for common operations
async def quick_generate(natural_language_input: str, 
                        config_path: str = "config/config.yaml") -> GenerationResult:
    """
    Quick configuration generation for simple use cases.
    
    Args:
        natural_language_input: Natural language description
        config_path: Path to configuration file
        
    Returns:
        GenerationResult
    """
    framework = KubeNetLLMFramework(config_path)
    await framework.initialize()
    
    try:
        result = await framework.generate_configuration(natural_language_input)
        return result
    finally:
        await framework.shutdown()


async def quick_validate(configuration_path: str,
                        config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Quick validation of existing configuration.
    
    Args:
        configuration_path: Path to configuration file
        config_path: Path to framework configuration
        
    Returns:
        Validation results
    """
    framework = KubeNetLLMFramework(config_path)
    await framework.initialize()
    
    try:
        result = await framework.validate_existing_configuration(configuration_path)
        return result
    finally:
        await framework.shutdown() 