"""Ollama API client wrapper for OCA."""

import requests
from typing import Dict, Any, Optional
import json


class OllamaError(Exception):
    """Ollama API error."""
    pass


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, model: str = "codellama", api_url: str = "http://localhost:11434",
                 timeout: int = 120, max_tokens: int = 4096) -> None:
        """Initialize Ollama client.
        
        Args:
            model: Model name to use
            api_url: Ollama API URL
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.max_tokens = max_tokens
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 context: Optional[str] = None) -> str:
        """Generate response using Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            context: Additional context
            
        Returns:
            Generated response
            
        Raises:
            OllamaError: If API request fails
        """
        # Construct full prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        if context:
            full_prompt = f"Context:\n{context}\n\n{full_prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": 0.1,  # Lower temperature for more consistent code
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.RequestException as e:
            raise OllamaError(f"Failed to connect to Ollama: {e}")
        except (json.JSONDecodeError, ValueError) as e:
            raise OllamaError(f"Invalid response from Ollama: {e}")
        except KeyError as e:
            raise OllamaError(f"Unexpected response format: {e}")
    
    def list_models(self) -> list:
        """List available models.
        
        Returns:
            List of available models
            
        Raises:
            OllamaError: If API request fails
        """
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get("models", [])
            
        except requests.exceptions.RequestException as e:
            raise OllamaError(f"Failed to connect to Ollama: {e}")
        except json.JSONDecodeError as e:
            raise OllamaError(f"Invalid response from Ollama: {e}")
    
    def is_available(self) -> bool:
        """Check if Ollama is available.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False