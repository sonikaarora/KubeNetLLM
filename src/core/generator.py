"""
Configuration Generator with MCP Integration - Component 2 of KubeNetLLM architecture.
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import os

import structlog
import yaml
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from ..utils.exceptions import GenerationError, LLMError
from .llm_providers import FreeLLMManager, LLMResponse

logger = structlog.get_logger(__name__)


@dataclass
class GenerationMetrics:
    """Metrics for configuration generation"""
    api_calls: int = 0
    tokens_used: int = 0
    generation_time: float = 0.0
    template_hits: int = 0
    context_retrievals: int = 0


class ConfigurationGenerator:
    """
    Configuration Generator with MCP Integration - Component 2 of KubeNetLLM architecture.
    Generates Kubernetes configurations using LLMs enhanced with MCP.
    """

    def __init__(self, config: Dict[str, Any], mcp_broker=None):
        """
        Initialize the Configuration Generator.
        
        Args:
            config: LLM configuration
            mcp_broker: MCP broker instance
        """
        self.config = config
        self.mcp_broker = mcp_broker
        self.logger = structlog.get_logger(__name__)
        self.metrics = GenerationMetrics()
        
        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None
        self.free_llm_manager = None
        
        # Setup based on provider
        self.provider = config.get("default_provider", "openai")
        self._setup_llm_clients()
        
        # Load templates
        self.templates = self._load_templates()
        
        self.logger.info("Configuration Generator initialized", 
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
        
        # If using free providers as default, log available options
        if self.provider == "free" and self.free_llm_manager:
            available = self.free_llm_manager.get_available_providers()
            if available:
                self.logger.info("Using free LLM providers", available=available)
            else:
                raise LLMError("No free LLM providers available! Please set up Ollama, Groq, or another provider.")

    def _load_templates(self) -> Dict[str, str]:
        """Load base templates for common scenarios"""
        return {
            "web_app": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app: {app_name}
    tier: frontend
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
        tier: frontend
    spec:
      containers:
      - name: {app_name}
        image: {image}
        ports:
        - containerPort: {port}
        resources:
          requests:
            cpu: {cpu_request}
            memory: {memory_request}
          limits:
            cpu: {cpu_limit}
            memory: {memory_limit}
        livenessProbe:
          httpGet:
            path: /
            port: {port}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}-service
  namespace: {namespace}
  labels:
    app: {app_name}
spec:
  selector:
    app: {app_name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: {port}
  type: ClusterIP
""",
            "microservice": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service_name}
  namespace: {namespace}
  labels:
    app: {service_name}
    tier: backend
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {service_name}
  template:
    metadata:
      labels:
        app: {service_name}
        tier: backend
    spec:
      containers:
      - name: {service_name}
        image: {image}
        ports:
        - containerPort: {port}
        env:
        - name: SERVICE_NAME
          value: {service_name}
        resources:
          requests:
            cpu: {cpu_request}
            memory: {memory_request}
          limits:
            cpu: {cpu_limit}
            memory: {memory_limit}
        livenessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {namespace}
  labels:
    app: {service_name}
spec:
  selector:
    app: {service_name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: {port}
  type: ClusterIP
""",
            "database": """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {db_name}
  namespace: {namespace}
  labels:
    app: {db_name}
    tier: database
spec:
  serviceName: {db_name}
  replicas: {replicas}
  selector:
    matchLabels:
      app: {db_name}
  template:
    metadata:
      labels:
        app: {db_name}
        tier: database
    spec:
      containers:
      - name: {db_name}
        image: {image}
        ports:
        - containerPort: {port}
        env:
        - name: POSTGRES_DB
          value: {database_name}
        - name: POSTGRES_USER
          value: {username}
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {db_name}-secret
              key: password
        resources:
          requests:
            cpu: {cpu_request}
            memory: {memory_request}
            storage: {storage_request}
          limits:
            cpu: {cpu_limit}
            memory: {memory_limit}
        volumeMounts:
        - name: {db_name}-storage
          mountPath: /var/lib/postgresql/data
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 999
  volumeClaimTemplates:
  - metadata:
      name: {db_name}-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: {storage_request}
---
apiVersion: v1
kind: Service
metadata:
  name: {db_name}
  namespace: {namespace}
  labels:
    app: {db_name}
spec:
  selector:
    app: {db_name}
  ports:
    - protocol: TCP
      port: 5432
      targetPort: {port}
  type: ClusterIP
  clusterIP: None
---
apiVersion: v1
kind: Secret
metadata:
  name: {db_name}-secret
  namespace: {namespace}
type: Opaque
data:
  password: {password_base64}
""",
            "network_policy": """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {policy_name}
  namespace: {namespace}
spec:
  podSelector:
    matchLabels:
      app: {app_name}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: {allowed_tier}
    ports:
    - protocol: TCP
      port: {port}
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: database
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
""",
            "ingress": """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}-ingress
  namespace: {namespace}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - {hostname}
    secretName: {app_name}-tls
  rules:
  - host: {hostname}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {app_name}-service
            port:
              number: 80
"""
        }

    async def generate_configurations(self, 
                                    requirements: Any,
                                    context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate Kubernetes configurations from processed requirements.
        
        Args:
            requirements: Processed requirements from NL interface
            context: Additional context for generation
            
        Returns:
            List of Kubernetes configuration dictionaries
        """
        start_time = time.time()
        self.metrics = GenerationMetrics()
        
        try:
            self.logger.info("Starting configuration generation",
                           requirements_count=len(requirements.requirements) if hasattr(requirements, 'requirements') else 0)
            
            # Step 1: Analyze requirements
            analysis = await self._analyze_requirements(requirements, context)
            self.metrics.api_calls += 1
            
            # Step 2: Retrieve context via MCP
            enhanced_context = await self._retrieve_context(analysis, context)
            self.metrics.context_retrievals += 1
            
            # Step 3: Generate configurations
            configurations = await self._generate_configurations(
                requirements, analysis, enhanced_context
            )
            
            # Step 4: Post-process configurations
            processed_configs = self._post_process_configurations(configurations)
            
            self.metrics.generation_time = time.time() - start_time
            
            self.logger.info("Configuration generation completed",
                           config_count=len(processed_configs),
                           generation_time=self.metrics.generation_time,
                           api_calls=self.metrics.api_calls)
            
            return processed_configs
            
        except Exception as e:
            self.logger.error("Configuration generation failed", error=str(e))
            raise GenerationError(f"Failed to generate configurations: {e}")

    async def _analyze_requirements(self, requirements: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze requirements and extract key components"""
        # If requirements is already processed, extract info
        if hasattr(requirements, 'requirements'):
            analysis = {
                "components": [],
                "networking": requirements.networking,
                "security": requirements.security,
                "global_settings": requirements.global_settings
            }
            
            for req in requirements.requirements:
                component = {
                    "type": req.type,
                    "name": req.name,
                    "description": req.description,
                    "replicas": req.replicas,
                    "ports": req.ports,
                    "environment": req.environment,
                    "dependencies": req.dependencies,
                    "security_level": req.security_level,
                    "resource_requirements": req.resource_requirements
                }
                analysis["components"].append(component)
            
            return analysis
        
        # If requirements is a string, analyze with LLM
        if isinstance(requirements, str):
            prompt = f"""
            Analyze the following Kubernetes deployment requirements and extract key components:
            
            Requirements: {requirements}
            
            Extract:
            1. Application components (web, api, database, etc.)
            2. Security requirements
            3. Networking needs
            4. Scaling requirements
            5. Resource requirements
            
            Return as JSON with structure:
            {{
                "components": [
                    {{
                        "type": "web_app|microservice|database",
                        "name": "component_name",
                        "replicas": 3,
                        "ports": [80],
                        "resource_requirements": {{"cpu": "500m", "memory": "1Gi"}},
                        "security_level": "medium"
                    }}
                ],
                "networking": {{"ingress": true, "service_mesh": false}},
                "security": {{"network_policies": true, "tls_required": true}},
                "global_settings": {{"namespace": "default", "environment": "production"}}
            }}
            """
            
            system_prompt = "You are a Kubernetes expert. Always return valid JSON."
            
            # Try free providers first
            if self.provider == "free" and self.free_llm_manager:
                try:
                    response = await self._call_free_llm(prompt, system_prompt)
                    return response
                except Exception as e:
                    self.logger.warning("Free LLM call failed, trying paid providers", error=str(e))
            
            # Fallback to paid providers
            if self.openai_client:
                response = await self._call_openai(prompt)
                return response
            elif self.anthropic_client:
                response = await self._call_anthropic(prompt, system_prompt)
                return response
            else:
                raise LLMError("No LLM providers available! Please set up Ollama, Groq, or another provider.")
        
        return {}

    async def _retrieve_context(self, analysis: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieve relevant context via MCP"""
        enhanced_context = context or {}
        
        if self.mcp_broker:
            try:
                # Get cluster information
                cluster_info = await self.mcp_broker.invoke_tool(
                    "cluster_info", 
                    {"resource_type": "all"}
                )
                enhanced_context["cluster"] = cluster_info
                
                # Get security policies if needed
                if analysis.get("security", {}).get("network_policies"):
                    policies = await self.mcp_broker.invoke_tool(
                        "security_policies",
                        {"policy_type": "network"}
                    )
                    enhanced_context["policies"] = policies
                
                # Get documentation for complex scenarios
                if len(analysis.get("components", [])) > 3:
                    docs = await self.mcp_broker.invoke_tool(
                        "kubernetes_docs",
                        {"query": "microservices best practices"}
                    )
                    enhanced_context["docs"] = docs
                    
            except Exception as e:
                self.logger.warning("MCP context retrieval failed", error=str(e))
        
        return enhanced_context

    async def _generate_configurations(self, 
                                     requirements: Any, 
                                     analysis: Dict[str, Any],
                                     context: Dict[str, Any]) -> List[str]:
        """Generate actual Kubernetes configurations"""
        configurations = []
        
        # Generate configurations for each component
        for component in analysis.get("components", []):
            config = await self._generate_component_config(component, analysis, context)
            if config:
                configurations.append(config)
                self.metrics.template_hits += 1
        
        # Generate networking configurations
        networking_config = await self._generate_networking_config(analysis, context)
        if networking_config:
            configurations.append(networking_config)
        
        # Generate security configurations
        security_config = await self._generate_security_config(analysis, context)
        if security_config:
            configurations.append(security_config)
        
        return configurations

    async def _generate_component_config(self, 
                                       component: Dict[str, Any],
                                       analysis: Dict[str, Any],
                                       context: Dict[str, Any]) -> Optional[str]:
        """Generate configuration for a single component"""
        component_type = component.get("type", "web_app")
        
        # Get template
        template = self.templates.get(component_type, self.templates["web_app"])
        
        # Prepare template parameters
        params = {
            "app_name": component.get("name", "app"),
            "service_name": component.get("name", "service"),
            "db_name": component.get("name", "database"),
            "namespace": analysis.get("global_settings", {}).get("namespace", "default"),
            "replicas": component.get("replicas", 2),
            "port": component.get("ports", [80])[0] if component.get("ports") else 80,
            "image": self._get_default_image(component_type),
            "cpu_request": component.get("resource_requirements", {}).get("cpu", "250m"),
            "memory_request": component.get("resource_requirements", {}).get("memory", "512Mi"),
            "cpu_limit": component.get("resource_requirements", {}).get("cpu", "500m"),
            "memory_limit": component.get("resource_requirements", {}).get("memory", "1Gi"),
            "storage_request": component.get("resource_requirements", {}).get("storage", "10Gi"),
            "database_name": component.get("name", "app") + "db",
            "username": "appuser",
            "password_base64": "cGFzc3dvcmQxMjM=",  # password123 base64 encoded
        }
        
        # Format template
        try:
            return template.format(**params)
        except KeyError as e:
            self.logger.warning("Template formatting failed", error=str(e), component=component_type)
            return None

    def _get_default_image(self, component_type: str) -> str:
        """Get default container image for component type"""
        image_map = {
            "web_app": "nginx:1.21-alpine",
            "microservice": "node:18-alpine",
            "database": "postgres:15-alpine",
            "cache": "redis:7-alpine",
            "queue": "rabbitmq:3-alpine"
        }
        return image_map.get(component_type, "nginx:1.21-alpine")

    async def _generate_networking_config(self, 
                                        analysis: Dict[str, Any],
                                        context: Dict[str, Any]) -> Optional[str]:
        """Generate networking configurations (ingress, network policies)"""
        networking = analysis.get("networking", {})
        
        if networking.get("ingress"):
            template = self.templates["ingress"]
            params = {
                "app_name": analysis.get("components", [{}])[0].get("name", "app"),
                "namespace": analysis.get("global_settings", {}).get("namespace", "default"),
                "hostname": f"{analysis.get('components', [{}])[0].get('name', 'app')}.local"
            }
            
            try:
                return template.format(**params)
            except KeyError as e:
                self.logger.warning("Ingress template formatting failed", error=str(e))
        
        return None

    async def _generate_security_config(self, 
                                      analysis: Dict[str, Any],
                                      context: Dict[str, Any]) -> Optional[str]:
        """Generate security configurations (network policies, RBAC)"""
        security = analysis.get("security", {})
        
        if security.get("network_policies"):
            configs = []
            
            # Generate network policies for each component
            for component in analysis.get("components", []):
                template = self.templates["network_policy"]
                params = {
                    "policy_name": f"{component.get('name', 'app')}-netpol",
                    "namespace": analysis.get("global_settings", {}).get("namespace", "default"),
                    "app_name": component.get("name", "app"),
                    "port": component.get("ports", [80])[0] if component.get("ports") else 80,
                    "allowed_tier": "frontend" if component.get("type") == "web_app" else "backend"
                }
                
                try:
                    config = template.format(**params)
                    configs.append(config)
                except KeyError as e:
                    self.logger.warning("Network policy template formatting failed", error=str(e))
            
            return "\n---\n".join(configs) if configs else None
        
        return None

    def _post_process_configurations(self, configurations: List[str]) -> List[Dict[str, Any]]:
        """Post-process configurations and convert to dictionaries"""
        processed_configs = []
        
        for config_yaml in configurations:
            if not config_yaml:
                continue
                
            try:
                # Parse YAML documents
                documents = yaml.safe_load_all(config_yaml)
                for doc in documents:
                    if doc:
                        processed_configs.append(doc)
                        
            except yaml.YAMLError as e:
                self.logger.warning("YAML parsing failed", error=str(e))
                continue
        
        return processed_configs

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
            self.metrics.tokens_used += response.tokens_used
            self.metrics.api_calls += 1
            
            # Extract JSON from response
            json_data = self.free_llm_manager.extract_json_from_response(response)
            
            # If extraction failed, try manual parsing
            if "error" in json_data:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            
            return json_data
            
        except Exception as e:
            self.logger.error("Free LLM API call failed", error=str(e))
            raise LLMError(f"Free LLM API call failed: {e}")

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            provider_config = self.config.get("providers", {}).get("openai", {})
            
            response = await self.openai_client.chat.completions.create(
                model=provider_config.get("model", "gpt-4"),
                messages=[
                    {"role": "system", "content": "You are a Kubernetes expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=provider_config.get("max_tokens", 4096),
                temperature=provider_config.get("temperature", 0.1)
            )
            
            content = response.choices[0].message.content
            self.metrics.tokens_used += response.usage.total_tokens
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            self.logger.error("OpenAI API call failed", error=str(e))
            raise LLMError(f"OpenAI API call failed: {e}")
    
    async def _call_anthropic(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """Call Anthropic API"""
        try:
            provider_config = self.config.get("providers", {}).get("anthropic", {})
            
            message = await self.anthropic_client.messages.create(
                model=provider_config.get("model", "claude-3-sonnet-20240229"),
                max_tokens=provider_config.get("max_tokens", 4096),
                temperature=provider_config.get("temperature", 0.1),
                system=system_prompt or "You are a Kubernetes expert. Always return valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text
            self.metrics.tokens_used += message.usage.input_tokens + message.usage.output_tokens
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            self.logger.error("Anthropic API call failed", error=str(e))
            raise LLMError(f"Anthropic API call failed: {e}")



    def get_api_call_count(self) -> int:
        """Get number of API calls made"""
        return self.metrics.api_calls

    def get_token_usage(self) -> int:
        """Get total tokens used"""
        return self.metrics.tokens_used

    def get_generation_metrics(self) -> GenerationMetrics:
        """Get detailed generation metrics"""
        return self.metrics 