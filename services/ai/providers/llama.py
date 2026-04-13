import os
import requests
from pathlib import Path
from tqdm import tqdm
from llama_cpp import Llama
from services.core.logger_service import setup_logger

logger = setup_logger("AI.Llama")

class LlamaProvider:
    """Handles local GGUF models and embedding generation."""
    
    DEFAULT_MODEL_URL = "https://huggingface.co/mradermacher/paraphrase-multilingual-MiniLM-L12-v2-GGUF/resolve/main/paraphrase-multilingual-MiniLM-L12-v2.I1-Q8_0.gguf"
    DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2.I1-Q8_0.gguf"

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.models_dir / self.DEFAULT_MODEL_NAME
        self.client = None
        self.is_ready = False

    def ensure_model(self):
        if self.model_path.exists():
            logger.info(f"Model exists: {self.model_path}")
            return
        
        logger.info(f"Downloading model to {self.model_path}...")
        response = requests.get(self.DEFAULT_MODEL_URL, stream=True)
        with open(self.model_path, "wb") as f:
            for data in response.iter_content(1024*1024): f.write(data)
        logger.info("Download complete.")

    def initialize(self):
        try:
            self.ensure_model()
            # If the model is corrupt or invalid, this is where it crashes usually.
            # We wrap it to allow the server to start anyway.
            self.client = Llama(model_path=str(self.model_path), embedding=True, verbose=False)
            self.is_ready = True
            logger.info("LlamaProvider initialized successfully.")
        except Exception as e:
            self.is_ready = False
            logger.error(f"Llama initialization deferred or failed: {e}")
            # Do NOT raise, just stay un-ready.

    async def get_embeddings(self, text: str):
        if not self.client: 
            self.initialize()
        
        if not self.is_ready:
            return [0.0] * 384 # Fallback zero vector if failed
            
        try:
            res = self.client.create_embedding(text)
            return res['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 384
