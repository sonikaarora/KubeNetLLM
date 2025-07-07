"""
Custom exceptions for KubeNetLLM framework.
"""


class KubeNetLLMException(Exception):
    """Base exception for KubeNetLLM framework"""
    pass


class ConfigurationError(KubeNetLLMException):
    """Raised when configuration is invalid"""
    pass


class ValidationError(KubeNetLLMException):
    """Raised when validation fails"""
    pass


class GenerationError(KubeNetLLMException):
    """Raised when configuration generation fails"""
    pass


class DeploymentError(KubeNetLLMException):
    """Raised when deployment fails"""
    pass


class MCPError(KubeNetLLMException):
    """Raised when MCP operations fail"""
    pass


class LLMError(KubeNetLLMException):
    """Raised when LLM operations fail"""
    pass


class KubernetesError(KubeNetLLMException):
    """Raised when Kubernetes operations fail"""
    pass


class SecurityError(KubeNetLLMException):
    """Raised when security validation fails"""
    pass


class ContextError(KubeNetLLMException):
    """Raised when context processing fails"""
    pass 