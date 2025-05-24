"""Ollama API client wrapper for OCA."""

import os
import requests
from typing import Dict, Any, Optional
import json


class OllamaError(Exception):
    """Ollama API error."""
    pass


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, model: str = "codellama", api_url: str = "http://localhost:11434",
                 timeout: int = 180, max_tokens: int = 4096) -> None:  # Increased default timeout
        """Initialize Ollama client.
        
        Args:
            model: Model name to use
            api_url: Ollama API URL
            timeout: Request timeout in seconds (default 180s for slow responses)
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.mock_mode = os.getenv('OCA_MOCK_OLLAMA', 'false').lower() == 'true'
        self.debug_mode = os.getenv('OCA_DEBUG', 'false').lower() == 'true'
    
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
        if self.mock_mode:
            return self._generate_mock_response(prompt, system_prompt, context)
        
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
        
        # Debug information
        url = f"{self.api_url}/api/generate"
        headers = {"Content-Type": "application/json"}
        
        if self.debug_mode:
            print(f"🔍 DEBUG: Ollama API Call")
            print(f"📍 URL: {url}")
            print(f"📋 Payload: {json.dumps(payload, indent=2)}")
            print(f"📦 Headers: {headers}")
            print(f"⏱️  Timeout: {self.timeout}s")
            print(f"🔄 Request about to be sent...")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if self.debug_mode:
                print(f"📡 Response Status: {response.status_code}")
                print(f"📄 Response Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"❌ Error Response Body: {response.text}")
                print(f"🔍 Full Response: {response}")
            
            response.raise_for_status()
            
            result = response.json()
            if self.debug_mode:
                print(f"✅ Response JSON: {json.dumps(result, indent=2)}")
            
            # Extract response field
            if "response" in result:
                response_text = result["response"].strip()
                if self.debug_mode:
                    print(f"📝 Extracted Response: {response_text[:100]}...")
                return response_text
            else:
                error_msg = f"No 'response' field in JSON. Available fields: {list(result.keys())}"
                print(f"⚠️  Warning: {error_msg}")
                return str(result)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {response.status_code}: {e}"
            if hasattr(response, 'text'):
                error_msg += f"\nResponse body: {response.text}"
            print(f"🚨 HTTPError: {error_msg}")
            raise OllamaError(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed to {url}: {e}"
            print(f"🚨 ConnectionError: {error_msg}")
            raise OllamaError(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {self.timeout}s: {e}"
            print(f"🚨 TimeoutError: {error_msg}")
            raise OllamaError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            print(f"🚨 RequestException: {error_msg}")
            raise OllamaError(error_msg)
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Invalid JSON response: {e}\nResponse text: {response.text if 'response' in locals() else 'N/A'}"
            print(f"🚨 JSONDecodeError: {error_msg}")
            raise OllamaError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"🚨 UnexpectedError: {error_msg}")
            raise OllamaError(error_msg)
    
    def _generate_mock_response(self, prompt: str, system_prompt: Optional[str] = None,
                               context: Optional[str] = None) -> str:
        """Generate mock response for testing.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            context: Additional context
            
        Returns:
            Mock response based on prompt content
        """
        prompt_lower = prompt.lower()
        
        # Mock responses based on command type
        if "explain" in prompt_lower or "what does" in prompt_lower:
            if context and "def hello" in context:
                return """This code defines a simple `hello()` function that prints "Hello, World!" to the console. 

**Function breakdown:**
- `def hello():` - Defines a function named 'hello' with no parameters
- `print('Hello, World!')` - Outputs the classic greeting message

This is a basic example function commonly used for testing or as a simple introduction to programming."""
            
            return """This code appears to be a basic utility function. Based on the structure and naming patterns, it likely performs a specific operation within the application's workflow. 

To provide a more detailed explanation, I would need to see the specific code implementation and understand its context within the broader codebase."""
        
        elif "fix" in prompt_lower or "bug" in prompt_lower or "error" in prompt_lower:
            if "type" in prompt_lower:
                return """**Issue Identified:** TypeError - likely caused by incompatible data types in an operation.

**Recommended Fix:**
1. Add type checking before operations
2. Ensure consistent data types
3. Add proper error handling

```python
def fixed_function(a, b):
    # Add type validation
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numeric")
    
    try:
        result = a + b
        return result
    except Exception as e:
        print(f"Error in calculation: {e}")
        return None
```

This fix adds type validation and error handling to prevent TypeErrors."""
            
            return """**Issue Analysis:** Based on the error description, here's a systematic approach to fix the problem:

1. **Identify root cause** - Review the error traceback and context
2. **Implement defensive coding** - Add input validation and error handling
3. **Test the fix** - Ensure the solution works for edge cases

**Recommended approach:**
- Add proper exception handling
- Validate inputs before processing
- Include logging for debugging future issues"""
        
        elif "refactor" in prompt_lower:
            return """**Refactoring Recommendations:**

1. **Code Structure Improvements:**
   - Extract common functionality into reusable functions
   - Apply single responsibility principle
   - Improve naming conventions for better readability

2. **Modern Language Features:**
   - Use type hints for better code documentation
   - Implement context managers where appropriate
   - Consider async/await patterns for I/O operations

3. **Performance Optimizations:**
   - Replace loops with list comprehensions where suitable
   - Use built-in functions for common operations
   - Consider caching for expensive computations

The refactored code will be more maintainable, readable, and efficient."""
        
        elif "test" in prompt_lower and ("generate" in prompt_lower or "create" in prompt_lower):
            return """**Test Suite Generated:**

```python
import pytest
from unittest.mock import Mock, patch

class TestModule:
    def test_basic_functionality(self):
        \"\"\"Test basic function behavior.\"\"\"
        # Arrange
        expected_result = "expected_value"
        
        # Act
        result = function_under_test()
        
        # Assert
        assert result == expected_result
    
    def test_edge_cases(self):
        \"\"\"Test edge cases and error conditions.\"\"\"
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
    
    def test_with_mocks(self):
        \"\"\"Test with mocked dependencies.\"\"\"
        with patch('module.dependency') as mock_dep:
            mock_dep.return_value = "mocked_value"
            result = function_under_test()
            assert result is not None
```

**Test Coverage:**
- Happy path scenarios
- Edge cases and error conditions
- Mocked external dependencies
- Input validation tests"""
        
        elif "commit" in prompt_lower:
            if context and ("git status" in context.lower() or "git diff" in context.lower()):
                return "feat: implement file scanning and search functionality\n\n- Add FileScanner class for codebase analysis\n- Enhance search command with regex and type filtering\n- Improve commit command with actual git diff context\n- Add function and class detection capabilities"
            
            return "feat: add new functionality\n\nImplement core feature with proper error handling and tests.\nIncludes documentation and follows conventional commit format."
        
        elif "search" in prompt_lower or "find" in prompt_lower:
            if "function" in prompt_lower:
                return """**Functions Found in Codebase:**

**hello.py:**
- `hello()` (line 1) - Simple greeting function

**oca/core/ollama.py:**
- `generate()` (line 33) - Main AI generation method
- `_generate_mock_response()` (line 85) - Mock response generator
- `list_models()` (line 120) - Available models listing
- `is_available()` (line 145) - Service availability check

**oca/utils/git.py:**
- `_run_git()` (line 25) - Git command execution
- `create_worktree()` (line 85) - Worktree management
- `get_diff()` (line 175) - Git diff retrieval

These functions represent the core functionality of the OCA system."""
            
            return """**Search Results:**

Based on your search criteria, I found several relevant code patterns and implementations in the codebase. The search focused on the most commonly used functions and patterns.

**Key findings:**
- Multiple utility functions for file operations
- Error handling patterns throughout the codebase
- Configuration management implementations
- Git integration workflows

For more specific searches, try using regex patterns or specifying the search type (function, class, comment)."""
        
        else:
            return f"""**AI Assistant Response:**

I understand you're asking about: "{prompt}"

Based on the context provided, I can help you with code analysis, bug fixes, refactoring suggestions, test generation, and codebase searches. 

**What I can do:**
- Explain code functionality and architecture
- Identify and fix bugs with detailed solutions
- Suggest refactoring improvements
- Generate comprehensive test suites
- Search and analyze your codebase
- Create descriptive commit messages

Please provide more specific details about what you'd like me to help you with."""
    
    def list_models(self) -> list:
        """List available models.
        
        Returns:
            List of available models
            
        Raises:
            OllamaError: If API request fails
        """
        if self.mock_mode:
            return [
                {"name": "codellama:7b", "size": "3.8GB"},
                {"name": "codellama:13b", "size": "7.3GB"},
                {"name": "llama2:7b", "size": "3.8GB"},
                {"name": "mistral:7b", "size": "4.1GB"}
            ]
        
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
        if self.mock_mode:
            return True
        
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama and return detailed information.
        
        Returns:
            Dictionary with connection test results
        """
        result = {
            "connected": False,
            "api_url": self.api_url,
            "model": self.model,
            "timeout": self.timeout,
            "error": None,
            "models": [],
            "response_time": None
        }
        
        if self.mock_mode:
            result["connected"] = True
            result["models"] = ["codellama", "llama2"]
            result["mock_mode"] = True
            return result
        
        import time
        start_time = time.time()
        
        try:
            print(f"🔍 Testing connection to {self.api_url}")
            
            # Test /api/tags endpoint
            tags_url = f"{self.api_url}/api/tags"
            print(f"📡 Testing endpoint: {tags_url}")
            
            response = requests.get(tags_url, timeout=10)
            result["response_time"] = time.time() - start_time
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📄 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result["connected"] = True
                try:
                    data = response.json()
                    result["models"] = [model.get("name", "unknown") for model in data.get("models", [])]
                    print(f"✅ Available models: {result['models']}")
                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse JSON: {e}")
                    print(f"📄 Raw response: {response.text}")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Connection failed: {result['error']}")
                
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time
            print(f"🚨 Connection error: {e}")
        
        return result