import os
import sys
from typing import List, Optional
from services.ai.model_service import ModelService
from services.core.logger_service import setup_logger

logger = setup_logger("LlamaService")

class LlamaService:
    """Service to generate embeddings locally using llama-cpp-python."""
    
    _instance = None
    _llm = None

    def __init__(self, model_path: str = None):
        self.model_service = ModelService()
        # If model_path is not provided, use ModelService to get the default path
        self.model_path = model_path or self.model_service.ensure_model()
        self._initialize_llm()

    def _initialize_llm(self):
        """Lazy initialization of the Llama instance."""
        if LlamaService._llm is None:
            try:
                from llama_cpp import Llama
                logger.info(f"Loading local embedding model from: {self.model_path}")
                
                # Check if file exists
                if not os.path.exists(self.model_path):
                    logger.error(f"Model file not found: {self.model_path}")
                    return

                LlamaService._llm = Llama(
                    model_path=self.model_path,
                    embedding=True,
                    verbose=False,  # Set to True for debugging llama.cpp output
                    n_ctx=512,      # Standard context window
                    n_threads=os.cpu_count() or 4
                )
                logger.info("LlamaService | Local model loaded successfully.")
            except ImportError:
                logger.error("LlamaService | llama-cpp-python is not installed.")
            except Exception as e:
                logger.error(f"LlamaService | Failed to load model: {e}")

    def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for a single string."""
        if LlamaService._llm is None:
            self._initialize_llm()
            if LlamaService._llm is None:
                return []

        try:
            # llama-cpp-python v0.2.x+ API
            output = LlamaService._llm.create_embedding(text)
            return output['data'][0]['embedding']
        except Exception as e:
            logger.error(f"LlamaService | Embedding generation failed: {e}")
            return []

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of strings."""
        return [self.get_embeddings(t) for t in texts]

    @property
    def is_ready(self) -> bool:
        return LlamaService._llm is not None
