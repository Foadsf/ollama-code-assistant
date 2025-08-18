import os
import requests
import json

class GeminiAdapter:
    def __init__(self, model: str = "gemini-1.5-flash"):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = model
    
    def generate(self, prompt, system_prompt=None, context=None):
        """
        Mimic Ollama's generate method but use Gemini API
        """
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        full_prompt = []
        if system_prompt:
            full_prompt.append(system_prompt)
        if context:
            full_prompt.append("\n--- CONTEXT ---\
")
            full_prompt.append(context)
        full_prompt.append("\n--- PROMPT ---\
")
        full_prompt.append(prompt)

        payload = {
            "contents": [{"parts": [{"text": "".join(full_prompt)}]} ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            # Extract text from Gemini response format
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

