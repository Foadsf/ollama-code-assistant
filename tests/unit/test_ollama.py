"""Tests for Ollama client."""

import pytest
import requests
from unittest.mock import Mock, patch
from oca.core.ollama import OllamaClient, OllamaError


class TestOllamaClient:
    """Test cases for OllamaClient."""
    
    def test_init(self):
        """Test OllamaClient initialization."""
        client = OllamaClient(
            model="testmodel",
            api_url="http://test:1234",
            timeout=60,
            max_tokens=2048
        )
        
        assert client.model == "testmodel"
        assert client.api_url == "http://test:1234"
        assert client.timeout == 60
        assert client.max_tokens == 2048
    
    def test_init_defaults(self):
        """Test OllamaClient initialization with defaults."""
        client = OllamaClient()
        
        assert client.model == "codellama"
        assert client.api_url == "http://localhost:11434"
        assert client.timeout == 120
        assert client.max_tokens == 4096
    
    @patch('requests.post')
    def test_generate_success(self, mock_post):
        """Test successful generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Generated code here"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = OllamaClient(model="testmodel")
        result = client.generate("Fix the bug")
        
        assert result == "Generated code here"
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "testmodel",
                "prompt": "Fix the bug",
                "stream": False,
                "options": {
                    "num_predict": 4096,
                    "temperature": 0.1,
                }
            },
            timeout=120
        )
    
    @patch('requests.post')
    def test_generate_with_system_prompt(self, mock_post):
        """Test generation with system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "System response"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        result = client.generate(
            "Fix the bug",
            system_prompt="You are a code assistant"
        )
        
        assert result == "System response"
        
        # Check that system prompt was included
        call_args = mock_post.call_args
        prompt = call_args[1]['json']['prompt']
        assert "System: You are a code assistant" in prompt
        assert "User: Fix the bug" in prompt
    
    @patch('requests.post')
    def test_generate_with_context(self, mock_post):
        """Test generation with context."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Context-aware response"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        result = client.generate(
            "Explain this",
            context="def foo(): pass"
        )
        
        assert result == "Context-aware response"
        
        # Check that context was included
        call_args = mock_post.call_args
        prompt = call_args[1]['json']['prompt']
        assert "Context:\ndef foo(): pass" in prompt
    
    @patch('requests.post')
    def test_generate_request_exception(self, mock_post):
        """Test generation with request exception."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = OllamaClient()
        
        with pytest.raises(OllamaError, match="Failed to connect to Ollama"):
            client.generate("Fix the bug")
    
    @patch('requests.post')
    def test_generate_http_error(self, mock_post):
        """Test generation with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        
        with pytest.raises(OllamaError, match="Failed to connect to Ollama"):
            client.generate("Fix the bug")
    
    @patch('requests.post')
    def test_generate_invalid_json(self, mock_post):
        """Test generation with invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        
        with pytest.raises(OllamaError, match="Invalid response from Ollama"):
            client.generate("Fix the bug")
    
    @patch('requests.post')
    def test_generate_missing_response_key(self, mock_post):
        """Test generation with missing response key."""
        mock_response = Mock()
        mock_response.json.return_value = {"model": "testmodel"}  # Missing 'response' key
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        result = client.generate("Fix the bug")
        
        # Should return empty string when response key is missing
        assert result == ""
    
    @patch('requests.get')
    def test_list_models_success(self, mock_get):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "codellama:7b"},
                {"name": "llama2:13b"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        models = client.list_models()
        
        assert len(models) == 2
        assert models[0]["name"] == "codellama:7b"
        assert models[1]["name"] == "llama2:13b"
    
    @patch('requests.get')
    def test_list_models_error(self, mock_get):
        """Test model listing with error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = OllamaClient()
        
        with pytest.raises(OllamaError, match="Failed to connect to Ollama"):
            client.list_models()
    
    @patch('requests.get')
    def test_is_available_true(self, mock_get):
        """Test availability check when Ollama is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        assert client.is_available() is True
    
    @patch('requests.get')
    def test_is_available_false_bad_status(self, mock_get):
        """Test availability check with bad status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        client = OllamaClient()
        assert client.is_available() is False
    
    @patch('requests.get')
    def test_is_available_false_exception(self, mock_get):
        """Test availability check with connection exception."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = OllamaClient()
        assert client.is_available() is False