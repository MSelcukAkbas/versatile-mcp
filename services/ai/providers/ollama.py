import requests
from typing import List, Dict, Any, Optional
from services.core.logger_service import setup_logger

logger = setup_logger("AI.Ollama")

class OllamaProvider:
    """Handles communication with Ollama API."""
    
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host

    async def generate_completion(self, model: str, prompt: str, system: str = "") -> str:
        url = f"{self.host}/api/generate"
        payload = {"model": model, "prompt": prompt, "system": system, "stream": False}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Error: {e}"
