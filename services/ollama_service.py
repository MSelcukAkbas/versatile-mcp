import ollama
from services.logger_service import setup_logger
from typing import List, Dict, Any, Optional

logger = setup_logger("OllamaService")

class OllamaService:
    """Service to interact with local Ollama instance asynchronously."""
    
    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models in local Ollama."""
        try:
            response = await self.client.list()
            # Handle object-based response (newer versions)
            if hasattr(response, 'models'):
                return [m.model_dump() if hasattr(m, 'model_dump') else vars(m) for m in response.models]
            # Handle dictionary-based response (older versions)
            if isinstance(response, dict):
                return response.get('models', [])
            return []
        except Exception as e:
            return [{"error": str(e)}]

    async def show_model(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a specific Ollama model."""
        try:
            response = await self.client.show(name)
            if hasattr(response, 'model_dump'):
                return response.model_dump()
            if isinstance(response, dict):
                return response
            return vars(response)
        except Exception as e:
            return {"error": str(e)}

    async def generate_response(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response from a specific model."""
        try:
            response = await self.client.generate(
                model=model,
                prompt=prompt,
                system=system
            )
            return response.get('response', '')
        except Exception as e:
            return f"Error generating response: {str(e)}"

    async def chat(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Secure a chat completion from Ollama."""
        try:
            response = await self.client.chat(model=model, messages=messages)
            return response.get('message', {}).get('content', '')
        except Exception as e:
            return f"Error in chat: {str(e)}"
