#!/usr/bin/env python3
"""
Setup script for free LLM providers
Helps users get started with Ollama and other free providers
"""

import os
import subprocess
import sys
import time
import requests
import platform
from pathlib import Path


class FreeLLMSetup:
    """Setup helper for free LLM providers"""
    
    def __init__(self):
        self.system = platform.system().lower()
        print(f"🔧 Setting up free LLM providers on {self.system}")
    
    def check_ollama_installed(self) -> bool:
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Ollama is installed: {result.stdout.strip()}")
                return True
            else:
                print("❌ Ollama not found")
                return False
        except FileNotFoundError:
            print("❌ Ollama not installed")
            return False
    
    def install_ollama(self) -> bool:
        """Install Ollama"""
        print("📦 Installing Ollama...")
        
        if self.system == "darwin":  # macOS
            try:
                # Download and install Ollama for macOS
                download_url = "https://ollama.ai/download/Ollama-darwin.zip"
                print(f"Downloading Ollama from {download_url}")
                print("Please follow the installation instructions in your browser.")
                
                # Open the download page
                if os.system("command -v open > /dev/null 2>&1") == 0:
                    os.system("open https://ollama.ai/download")
                
                print("After installation, run: ollama serve")
                return True
                
            except Exception as e:
                print(f"❌ Failed to install Ollama on macOS: {e}")
                return False
        
        elif self.system == "linux":
            try:
                # Install Ollama on Linux
                result = subprocess.run([
                    "curl", "-fsSL", "https://ollama.ai/install.sh"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Run the installation script
                    install_result = subprocess.run([
                        "sh", "-c", result.stdout
                    ], capture_output=True, text=True)
                    
                    if install_result.returncode == 0:
                        print("✅ Ollama installed successfully")
                        return True
                    else:
                        print(f"❌ Failed to install Ollama: {install_result.stderr}")
                        return False
                else:
                    print(f"❌ Failed to download Ollama installer: {result.stderr}")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to install Ollama on Linux: {e}")
                return False
        
        else:
            print(f"❌ Unsupported system: {self.system}")
            print("Please install Ollama manually from https://ollama.ai")
            return False
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                print("✅ Ollama is running")
                return True
            else:
                print("❌ Ollama is not responding")
                return False
        except Exception as e:
            print("❌ Ollama is not running")
            return False
    
    def start_ollama(self) -> bool:
        """Start Ollama service"""
        print("🚀 Starting Ollama service...")
        
        try:
            # Start Ollama in the background
            if self.system == "darwin":
                # On macOS, Ollama might be an app
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # On Linux, start as a service
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for it to start
            print("⏳ Waiting for Ollama to start...")
            for i in range(30):
                time.sleep(1)
                if self.check_ollama_running():
                    return True
                print(".", end="", flush=True)
            
            print("\n❌ Ollama failed to start within 30 seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start Ollama: {e}")
            return False
    
    def list_available_models(self) -> list:
        """List available models"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
            else:
                return []
        except Exception as e:
            print(f"❌ Failed to list models: {e}")
            return []
    
    def pull_model(self, model_name: str = "llama3.2") -> bool:
        """Pull a model"""
        print(f"📥 Pulling model: {model_name}")
        print("This may take several minutes...")
        
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                print(f"✅ Successfully pulled {model_name}")
                return True
            else:
                print(f"❌ Failed to pull {model_name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout pulling {model_name}")
            return False
        except Exception as e:
            print(f"❌ Error pulling {model_name}: {e}")
            return False
    
    def setup_environment_variables(self):
        """Help user set up environment variables"""
        print("\n🔐 Optional: Set up API keys for additional providers")
        
        # Check for existing API keys
        groq_key = os.getenv("GROQ_API_KEY")
        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        
        if not groq_key:
            print("\n📝 To use Groq (fast inference):")
            print("1. Sign up at https://console.groq.com")
            print("2. Get your API key")
            print("3. Set environment variable: export GROQ_API_KEY=your_key_here")
        else:
            print("✅ GROQ_API_KEY is set")
        
        if not hf_key:
            print("\n📝 To use Hugging Face:")
            print("1. Sign up at https://huggingface.co")
            print("2. Get your API key from https://huggingface.co/settings/tokens")
            print("3. Set environment variable: export HUGGINGFACE_API_KEY=your_key_here")
        else:
            print("✅ HUGGINGFACE_API_KEY is set")
    
    def test_setup(self) -> bool:
        """Test the setup"""
        print("\n🧪 Testing setup...")
        
        # Test Ollama
        if not self.check_ollama_running():
            print("❌ Ollama is not running")
            return False
        
        models = self.list_available_models()
        if not models:
            print("❌ No models available in Ollama")
            return False
        
        print(f"✅ Available models: {', '.join(models)}")
        
        # Test a simple request
        try:
            import json
            
            payload = {
                "model": models[0],
                "prompt": "Hello, world!",
                "stream": False
            }
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Test successful: {result.get('response', 'No response')[:50]}...")
                return True
            else:
                print(f"❌ Test failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def run_setup(self):
        """Run complete setup"""
        print("🚀 KubeNetLLM Free LLM Setup")
        print("="*50)
        
        # Check if Ollama is installed
        if not self.check_ollama_installed():
            print("Installing Ollama...")
            if not self.install_ollama():
                print("❌ Failed to install Ollama")
                return False
        
        # Check if Ollama is running
        if not self.check_ollama_running():
            print("Starting Ollama...")
            if not self.start_ollama():
                print("❌ Failed to start Ollama")
                return False
        
        # Check for models
        models = self.list_available_models()
        if not models:
            print("No models found. Pulling llama3.2...")
            if not self.pull_model("llama3.2"):
                print("❌ Failed to pull model")
                return False
        else:
            print(f"✅ Available models: {', '.join(models)}")
        
        # Set up environment variables
        self.setup_environment_variables()
        
        # Test setup
        if self.test_setup():
            print("\n🎉 Setup completed successfully!")
            print("\nYou can now run:")
            print("  python3 real_experiment_runner.py")
            return True
        else:
            print("\n❌ Setup test failed")
            return False


def main():
    """Main setup function"""
    setup = FreeLLMSetup()
    setup.run_setup()


if __name__ == "__main__":
    main() 