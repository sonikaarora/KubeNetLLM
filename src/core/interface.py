"""
Natural Language Interface Engine for KubeNetLLM.
Component 1 of the 4-component architecture.
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import os

import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from ..utils.exceptions import LLMError, ContextError
from .llm_providers import FreeLLMManager, LLMResponse

logger = structlog.get_logger(__name__)


@dataclass
class ProcessedRequirement:
    """Processed requirement from natural language input"""
    type: str  # web_app, microservice, database, etc.
    name: str
    description: str
    security_level: str = "medium"
    replicas: int = 1
    ports: List[int] = field(default_factory=list)
    environment: str = "production"
    dependencies: List[str] = field(default_factory=list)
    network_policies: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, str] = field(default_factory=dict)
    custom_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedRequirements:
    """Collection of processed requirements"""
    requirements: List[ProcessedRequirement] = field(default_factory=list)
    global_settings: Dict[str, Any] = field(default_factory=dict)
    networking: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    clarifications_needed: List[str] = field(default_factory=list)


class NaturalLanguageInterface:
    """
    Natural Language Interface Engine - Component 1 of KubeNetLLM architecture.
    Processes natural language input and extracts structured requirements.
    """

    def __init__(self, config: Dict[str, Any], mcp_broker=None):
        """
        Initialize the Natural Language Interface.
        
        Args:
            config: LLM configuration
            mcp_broker: MCP broker instance
        """
        self.config = config
        self.mcp_broker = mcp_broker
        self.logger = structlog.get_logger(__name__)
        
        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None
        self.free_llm_manager = None
        
        # Metrics tracking
        self.api_calls = 0
        self.tokens_used = 0
        
        # Setup based on provider
        self.provider = config.get("default_provider", "openai")
        self._setup_llm_clients()
        
        # Prompt templates
        self.requirement_extraction_prompt = self._build_requirement_extraction_prompt()
        self.clarification_prompt = self._build_clarification_prompt()
        
        self.logger.info("Natural Language Interface initialized", 
                        provider=self.provider)

    def _setup_llm_clients(self):
        """Setup LLM clients based on configuration"""
        providers = self.config.get("providers", {})
        
        # OpenAI
        if "openai" in providers:
            openai_config = providers["openai"]
            api_key = openai_config.get("api_key") or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
        
        # Anthropic
        if "anthropic" in providers:
            anthropic_config = providers["anthropic"]
            api_key = anthropic_config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = AsyncAnthropic(api_key=api_key)
        
        # Setup Free LLM Manager
        if "free_providers" in self.config:
            # Load API keys from environment variables
            free_config = self.config.copy()
            if "groq" in free_config.get("free_providers", {}):
                free_config["free_providers"]["groq"]["api_key"] = os.getenv("GROQ_API_KEY", "")
            if "huggingface" in free_config.get("free_providers", {}):
                free_config["free_providers"]["huggingface"]["api_key"] = os.getenv("HUGGINGFACE_API_KEY", "")
            
            self.free_llm_manager = FreeLLMManager(free_config)
            
            # Check what providers are available
            available_providers = self.free_llm_manager.get_available_providers()
            self.logger.info("Free LLM providers available", providers=available_providers)

    def _build_requirement_extraction_prompt(self) -> str:
        """Build prompt for requirement extraction"""
        return """
You are a Kubernetes expert tasked with extracting structured requirements from natural language descriptions.

Extract the following information from the user's input:
1. Application components (web servers, databases, services, etc.)
2. Security requirements (network policies, TLS, authentication)
3. Networking requirements (ingress, service mesh, load balancing)
4. Resource requirements (CPU, memory, storage)
5. Environment settings (development, staging, production)
6. Dependencies between components

Return your analysis in the following JSON format:
{
    "requirements": [
        {
            "type": "web_app|microservice|database|cache|queue|other",
            "name": "component_name",
            "description": "detailed description",
            "security_level": "low|medium|high",
            "replicas": 1,
            "ports": [80, 443],
            "environment": "development|staging|production",
            "dependencies": ["other_component_names"],
            "network_policies": ["policy_descriptions"],
            "resource_requirements": {
                "cpu": "500m",
                "memory": "1Gi",
                "storage": "10Gi"
            },
            "custom_properties": {}
        }
    ],
    "global_settings": {
        "namespace": "default",
        "environment": "production",
        "monitoring": true,
        "logging": true
    },
    "networking": {
        "ingress_controller": "nginx",
        "service_mesh": "istio",
        "load_balancer": "external"
    },
    "security": {
        "network_policies": true,
        "pod_security_policies": true,
        "tls_required": true,
        "rbac": true
    },
    "clarifications_needed": [
        "List any unclear requirements that need clarification"
    ]
}

User Input: {input_text}

Analysis:
"""

    def _build_clarification_prompt(self) -> str:
        """Build prompt for seeking clarifications"""
        return """
Based on the following requirements analysis, generate specific clarifying questions to resolve ambiguities:

Analysis: {analysis}

Generate 3-5 specific questions that would help clarify the requirements:
"""

    async def process_input(self, 
                          natural_language_input: str,
                          context: Optional[Dict[str, Any]] = None) -> ProcessedRequirements:
        """
        Process natural language input and extract structured requirements.
        
        Args:
            natural_language_input: User's natural language description
            context: Additional context information
            
        Returns:
            ProcessedRequirements object
        """
        self.logger.info("Processing natural language input", 
                        input_length=len(natural_language_input))
        
        try:
            # Extract requirements using LLM
            requirements_json = await self._extract_requirements_with_llm(
                natural_language_input, context
            )
            
            # Parse and validate requirements
            processed_requirements = self._parse_requirements(requirements_json)
            
            # Enhance with context if available
            if context:
                processed_requirements = self._enhance_with_context(
                    processed_requirements, context
                )
            
            self.logger.info("Successfully processed requirements",
                           num_requirements=len(processed_requirements.requirements),
                           clarifications_needed=len(processed_requirements.clarifications_needed))
            
            return processed_requirements
            
        except Exception as e:
            self.logger.error("Failed to process natural language input", error=str(e))
            raise LLMError(f"Failed to process input: {e}")

    async def _extract_requirements_with_llm(self, 
                                           input_text: str,
                                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract requirements using LLM"""
        # Prepare context-enhanced prompt
        enhanced_input = input_text
        if context:
            context_str = f"Additional context: {context}\n\n"
            enhanced_input = context_str + input_text
        
        prompt = self.requirement_extraction_prompt.format(input_text=enhanced_input)
        system_prompt = "You are a Kubernetes expert. Always return valid JSON."
        
        # Try free providers first
        if self.provider == "free" and self.free_llm_manager:
            try:
                response = await self._call_free_llm(prompt, system_prompt)
                return response
            except Exception as e:
                self.logger.warning("Free LLM call failed, trying paid providers", error=str(e))
        
        # Call LLM based on provider
        if self.provider == "openai" and self.openai_client:
            return await self._call_openai(prompt)
        elif self.provider == "anthropic" and self.anthropic_client:
            return await self._call_anthropic(prompt)
        else:
            raise LLMError("No LLM providers available! Please set up Ollama, Groq, or another provider.")

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            provider_config = self.config.get("providers", {}).get("openai", {})
            
            response = await self.openai_client.chat.completions.create(
                model=provider_config.get("model", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=provider_config.get("max_tokens", 4096),
                temperature=provider_config.get("temperature", 0.1)
            )
            
            content = response.choices[0].message.content
            
            # Update metrics
            self.api_calls += 1
            self.tokens_used += response.usage.total_tokens
            
            # Extract JSON from response
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            self.logger.error("OpenAI API call failed", error=str(e))
            raise LLMError(f"OpenAI API call failed: {e}")

    async def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API"""
        try:
            provider_config = self.config.get("providers", {}).get("anthropic", {})
            
            response = await self.anthropic_client.messages.create(
                model=provider_config.get("model", "claude-3-sonnet-20240229"),
                max_tokens=provider_config.get("max_tokens", 4096),
                temperature=provider_config.get("temperature", 0.1),
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Update metrics
            self.api_calls += 1
            self.tokens_used += response.usage.input_tokens + response.usage.output_tokens
            
            # Extract JSON from response
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            self.logger.error("Anthropic API call failed", error=str(e))
            raise LLMError(f"Anthropic API call failed: {e}")

    async def _call_free_llm(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """Call free LLM provider"""
        try:
            preferred_provider = self.config.get("preferred_free_provider", "ollama")
            
            response = await self.free_llm_manager.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                preferred_provider=preferred_provider
            )
            
            # Update metrics
            self.api_calls += 1
            self.tokens_used += response.tokens_used
            
            # Extract JSON from response
            json_data = self.free_llm_manager.extract_json_from_response(response)
            
            # If extraction failed, try manual parsing
            if "error" in json_data:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    import json
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            
            return json_data
            
        except Exception as e:
            self.logger.error("Free LLM API call failed", error=str(e))
            raise LLMError(f"Free LLM API call failed: {e}")



    def _parse_requirements(self, requirements_json: Dict[str, Any]) -> ProcessedRequirements:
        """Parse JSON requirements into ProcessedRequirements object"""
        processed_requirements = ProcessedRequirements()
        
        # Parse individual requirements
        for req_data in requirements_json.get("requirements", []):
            requirement = ProcessedRequirement(
                type=req_data.get("type", "other"),
                name=req_data.get("name", "unnamed"),
                description=req_data.get("description", ""),
                security_level=req_data.get("security_level", "medium"),
                replicas=req_data.get("replicas", 1),
                ports=req_data.get("ports", []),
                environment=req_data.get("environment", "production"),
                dependencies=req_data.get("dependencies", []),
                network_policies=req_data.get("network_policies", []),
                resource_requirements=req_data.get("resource_requirements", {}),
                custom_properties=req_data.get("custom_properties", {})
            )
            processed_requirements.requirements.append(requirement)
        
        # Parse global settings
        processed_requirements.global_settings = requirements_json.get("global_settings", {})
        processed_requirements.networking = requirements_json.get("networking", {})
        processed_requirements.security = requirements_json.get("security", {})
        processed_requirements.clarifications_needed = requirements_json.get("clarifications_needed", [])
        
        return processed_requirements

    def _enhance_with_context(self, 
                            processed_requirements: ProcessedRequirements,
                            context: Dict[str, Any]) -> ProcessedRequirements:
        """Enhance requirements with additional context"""
        # Add context-specific enhancements
        if "cluster_info" in context:
            cluster_info = context["cluster_info"]
            # Adjust resource requirements based on cluster capacity
            # Add cluster-specific networking configuration
            pass
        
        if "organization_policies" in context:
            policies = context["organization_policies"]
            # Apply organization-specific security policies
            # Adjust naming conventions
            pass
        
        return processed_requirements

    async def seek_clarifications(self, 
                                processed_requirements: ProcessedRequirements) -> List[str]:
        """
        Generate clarifying questions for ambiguous requirements.
        
        Args:
            processed_requirements: Processed requirements needing clarification
            
        Returns:
            List of clarifying questions
        """
        if not processed_requirements.clarifications_needed:
            return []
        
        # Use LLM to generate specific clarifying questions
        analysis = {
            "requirements": [req.__dict__ for req in processed_requirements.requirements],
            "clarifications_needed": processed_requirements.clarifications_needed
        }
        
        prompt = self.clarification_prompt.format(analysis=analysis)
        
        try:
            if self.provider == "openai" and self.openai_client:
                response = await self._call_openai(prompt)
                return response.get("questions", [])
            elif self.provider == "anthropic" and self.anthropic_client:
                response = await self._call_anthropic(prompt)
                return response.get("questions", [])
            else:
                raise LLMError("No LLM providers available! Please set up Ollama, Groq, or another provider.")
        except Exception as e:
            self.logger.error("Failed to generate clarifying questions", error=str(e))
            raise LLMError(f"Failed to generate clarifying questions: {e}")
    
    def get_api_call_count(self) -> int:
        """Get number of API calls made"""
        return self.api_calls
    
    def get_token_usage(self) -> int:
        """Get total tokens used"""
        return self.tokens_used 