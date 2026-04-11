import os
from services.core.logger_service import setup_logger
from typing import List, Dict

logger = setup_logger("PromptService")

class PromptService:
    """Service to manage and load prompt templates."""
    
    def __init__(self, prompts_path: str):
        self.prompts_path = os.path.abspath(prompts_path)
        if not os.path.exists(self.prompts_path):
            os.makedirs(self.prompts_path)

    def list_templates(self) -> List[str]:
        """List all available prompt templates."""
        return [f.replace('.txt', '') for f in os.listdir(self.prompts_path) if f.endswith('.txt')]

    def get_template(self, name: str) -> str:
        """Get the content of a specific prompt template."""
        file_path = os.path.join(self.prompts_path, f"{name}.txt")
        logger.debug(f"Checking template at: {file_path}")
        if not os.path.exists(file_path):
            logger.warning(f"Template not found at: {file_path}")
            return ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def save_template(self, name: str, content: str) -> str:
        """Save or update a prompt template."""
        file_path = os.path.join(self.prompts_path, f"{name}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Template '{name}' saved successfully."
