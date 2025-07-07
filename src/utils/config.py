"""
Configuration management for KubeNetLLM framework.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)


class ConfigManager:
    """Manages configuration for KubeNetLLM framework"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to main configuration file
        """
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self._load_config()
        
        logger.info("Configuration loaded", 
                   config_path=str(self.config_path))
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config_data = yaml.safe_load(f) or {}
            else:
                logger.warning("Configuration file not found, using defaults",
                             path=str(self.config_path))
                self.config_data = self._get_default_config()
                
        except Exception as e:
            logger.error("Failed to load configuration", 
                        error=str(e), 
                        path=str(self.config_path))
            self.config_data = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "llm": {
                "providers": {
                    "openai": {
                        "model": "gpt-4",
                        "api_key_env": "OPENAI_API_KEY",
                        "max_tokens": 4096,
                        "temperature": 0.1
                    }
                },
                "default_provider": "openai"
            },
            "mcp": {
                "broker": {
                    "host": "localhost",
                    "port": 8080
                }
            },
            "kubernetes": {
                "context": "kind-kubenet-test",
                "namespace": "default"
            },
            "validation": {
                "levels": ["syntactic", "semantic", "security", "best_practices"]
            },
            "deployment": {
                "dry_run": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "llm.providers.openai.model")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        keys = key.split('.')
        config = self.config_data
        
        # Navigate to parent dict
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value
        """
        return os.getenv(key, default)
    
    def get_llm_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get LLM configuration for specified provider.
        
        Args:
            provider: Provider name (defaults to configured default)
            
        Returns:
            LLM configuration dict
        """
        if provider is None:
            provider = self.get("llm.default_provider", "openai")
            
        provider_config = self.get(f"llm.providers.{provider}", {})
        
        # Resolve API key from environment
        if "api_key_env" in provider_config:
            env_key = provider_config["api_key_env"]
            api_key = self.get_env(env_key)
            if api_key:
                provider_config["api_key"] = api_key
            else:
                logger.warning("API key not found in environment",
                             env_key=env_key,
                             provider=provider)
        
        return provider_config
    
    def get_kubernetes_config(self) -> Dict[str, Any]:
        """Get Kubernetes configuration"""
        return self.get("kubernetes", {})
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP configuration"""
        return self.get("mcp", {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration"""
        return self.get("validation", {})
    
    def get_deployment_config(self) -> Dict[str, Any]:
        """Get deployment configuration"""
        return self.get("deployment", {})
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._load_config()
        logger.info("Configuration reloaded")
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            path: Output path (defaults to original config path)
        """
        output_path = Path(path) if path else self.config_path
        
        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
                
            logger.info("Configuration saved", path=str(output_path))
            
        except Exception as e:
            logger.error("Failed to save configuration", 
                        error=str(e), 
                        path=str(output_path))
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return self.config_data.copy()
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if configuration is valid
        """
        required_keys = [
            "llm.providers",
            "llm.default_provider",
            "kubernetes.context",
            "mcp.broker.host",
            "mcp.broker.port"
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                logger.error("Missing required configuration", key=key)
                return False
        
        # Validate default provider exists
        default_provider = self.get("llm.default_provider")
        if not self.get(f"llm.providers.{default_provider}"):
            logger.error("Default LLM provider not configured", 
                        provider=default_provider)
            return False
        
        return True 