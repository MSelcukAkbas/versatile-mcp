import os
import logging
import asyncio
from typing import List, Optional

Llama = None

logger = logging.getLogger("LlamaProvider")


class LlamaProvider:
    """Provides local embeddings using llama-cpp."""

    def __init__(self, model_path: str, n_gpu_layers: int = -1, n_threads: int = 4):
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self._llm = None
        self._ready = False
        self._init_attempted = False
        self._lock = asyncio.Lock()

    def initialize(self):
        """Load the model. Safe to call multiple times — only loads once."""
        if self._init_attempted:
            return
        self._init_attempted = True

        global Llama
        if Llama is None:
            try:
                from llama_cpp import Llama
            except ImportError:
                logger.warning("llama-cpp-python not installed. Embeddings disabled.")
                return

        if not self.model_path or not os.path.exists(self.model_path):
            logger.warning(f"Model file not found: {self.model_path}. Embeddings disabled.")
            return

        from contextlib import redirect_stdout
        import sys

        try:
            with redirect_stdout(sys.stderr):
                self._llm = Llama(
                    model_path=self.model_path,
                    n_gpu_layers=self.n_gpu_layers,
                    n_threads=self.n_threads,
                    embedding=True,
                    verbose=False,
                )
            self._ready = True
            logger.info(f"Embedding model loaded: {os.path.basename(self.model_path)}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._ready = False

    async def get_embeddings(self, text: str) -> Optional[List[float]]:
        """
        Generate embeddings for text.
        Returns None on failure (not empty list — callers must check).
        """
        if not self._ready and not self._init_attempted:
            await asyncio.to_thread(self.initialize)

        if not self._ready or not self._llm:
            return None

        async with self._lock:
            try:
                result = await asyncio.to_thread(self._llm.create_embedding, text[:1500])
                embedding = result["data"][0]["embedding"]
                if not embedding:
                    return None
                return embedding
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                return None

    @property
    def is_ready(self) -> bool:
        return self._ready and self._llm is not None
