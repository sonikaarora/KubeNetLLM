"""
Free LLM Providers for KubeNetLLM Framework
Supports multiple free LLM providers including Ollama, Hugging Face, Groq, and LocalAI
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Any, Optional
import aiohttp
import requests
from dataclasses import dataclass

import structlog
from ..utils.exceptions import LLMError

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM provider"""
    content: str
    tokens_used: int = 0
    model: str = ""
    provider: str = ""
    response_time: float = 0.0


class OllamaProvider:
    """Ollama local LLM provider - completely free"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3.2")
        self.logger = structlog.get_logger(__name__)
        
    async def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate response using Ollama"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.get("temperature", 0.1),
                    "top_p": self.config.get("top_p", 0.9),
                    "max_tokens": self.config.get("max_tokens", 4096)
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        return LLMResponse(
                            content=result.get("response", ""),
                            tokens_used=result.get("eval_count", 0),
                            model=self.model,
                            provider="ollama",
                            response_time=time.time() - start_time
                        )
                    else:
                        raise LLMError(f"Ollama API error: {response.status}")
                        
        except Exception as e:
            self.logger.error("Ollama API call failed", error=str(e))
            raise LLMError(f"Ollama API call failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


class HuggingFaceProvider:
    """Hugging Face Inference API - free tier available"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "microsoft/DialoGPT-large")
        self.base_url = "https://api-inference.huggingface.co/models"
        self.logger = structlog.get_logger(__name__)
        
    async def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate response using Hugging Face"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}/{self.model}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Format prompt for different model types
            if system_prompt:
                formatted_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:"
            else:
                formatted_prompt = prompt
            
            payload = {
                "inputs": formatted_prompt,
                "parameters": {
                    "temperature": self.config.get("temperature", 0.1),
                    "max_new_tokens": self.config.get("max_tokens", 1000),
                    "return_full_text": False
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Handle different response formats
                        if isinstance(result, list) and len(result) > 0:
                            content = result[0].get("generated_text", "")
                        else:
                            content = str(result)
                        
                        return LLMResponse(
                            content=content,
                            tokens_used=len(content.split()),  # Approximate
                            model=self.model,
                            provider="huggingface",
                            response_time=time.time() - start_time
                        )
                    else:
                        raise LLMError(f"Hugging Face API error: {response.status}")
                        
        except Exception as e:
            self.logger.error("Hugging Face API call failed", error=str(e))
            raise LLMError(f"Hugging Face API call failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Hugging Face API is available"""
        return bool(self.api_key)


class GroqProvider:
    """Groq API - free tier with fast inference"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "llama3-8b-8192")
        self.base_url = "https://api.groq.com/openai/v1"
        self.logger = structlog.get_logger(__name__)
        
    async def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate response using Groq"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.config.get("temperature", 0.1),
                "max_tokens": self.config.get("max_tokens", 4096)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        content = result["choices"][0]["message"]["content"]
                        tokens_used = result.get("usage", {}).get("total_tokens", 0)
                        
                        return LLMResponse(
                            content=content,
                            tokens_used=tokens_used,
                            model=self.model,
                            provider="groq",
                            response_time=time.time() - start_time
                        )
                    else:
                        raise LLMError(f"Groq API error: {response.status}")
                        
        except Exception as e:
            self.logger.error("Groq API call failed", error=str(e))
            raise LLMError(f"Groq API call failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Groq API is available"""
        return bool(self.api_key)


class LocalAIProvider:
    """LocalAI - OpenAI-compatible local API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("base_url", "http://localhost:8080")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.logger = structlog.get_logger(__name__)
        
    async def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate response using LocalAI"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.config.get("temperature", 0.1),
                "max_tokens": self.config.get("max_tokens", 4096)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        content = result["choices"][0]["message"]["content"]
                        tokens_used = result.get("usage", {}).get("total_tokens", 0)
                        
                        return LLMResponse(
                            content=content,
                            tokens_used=tokens_used,
                            model=self.model,
                            provider="localai",
                            response_time=time.time() - start_time
                        )
                    else:
                        raise LLMError(f"LocalAI API error: {response.status}")
                        
        except Exception as e:
            self.logger.error("LocalAI API call failed", error=str(e))
            raise LLMError(f"LocalAI API call failed: {e}")
    
    def is_available(self) -> bool:
        """Check if LocalAI is available"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False


class FreeLLMManager:
    """Manager for free LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers = {}
        self.logger = structlog.get_logger(__name__)
        
        # Initialize providers
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize all configured providers"""
        providers_config = self.config.get("free_providers", {})
        
        # Ollama
        if "ollama" in providers_config:
            self.providers["ollama"] = OllamaProvider(providers_config["ollama"])
            
        # Hugging Face
        if "huggingface" in providers_config:
            self.providers["huggingface"] = HuggingFaceProvider(providers_config["huggingface"])
            
        # Groq
        if "groq" in providers_config:
            self.providers["groq"] = GroqProvider(providers_config["groq"])
            
        # LocalAI
        if "localai" in providers_config:
            self.providers["localai"] = LocalAIProvider(providers_config["localai"])
            
        self.logger.info("Free LLM providers initialized", 
                        providers=list(self.providers.keys()))
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        return available
    
    async def generate(self, prompt: str, system_prompt: str = None, 
                      preferred_provider: str = None) -> LLMResponse:
        """Generate response using the best available provider"""
        
        # Get available providers
        available_providers = self.get_available_providers()
        
        if not available_providers:
            raise LLMError("No free LLM providers available")
        
        # Choose provider
        if preferred_provider and preferred_provider in available_providers:
            provider_name = preferred_provider
        else:
            # Priority order: Ollama > Groq > LocalAI > Hugging Face
            priority_order = ["ollama", "groq", "localai", "huggingface"]
            provider_name = None
            for p in priority_order:
                if p in available_providers:
                    provider_name = p
                    break
            
            if not provider_name:
                provider_name = available_providers[0]
        
        provider = self.providers[provider_name]
        
        self.logger.info("Generating response", 
                        provider=provider_name, 
                        model=getattr(provider, 'model', 'unknown'))
        
        return await provider.generate(prompt, system_prompt)
    
    def extract_json_from_response(self, response: LLMResponse) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # If no JSON found, try to parse the entire response
            return json.loads(response.content)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return structured fallback
            return {
                "error": "Failed to parse JSON from response",
                "content": response.content
            } 