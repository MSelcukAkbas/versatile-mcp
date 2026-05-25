"""
Embedder — llama-cpp-python tabanlı embedding wrapper.

GGUF embedding modeli yükler ve metin listelerini vektöre dönüştürür.
Model yüklü değilse None döner (graceful degradation).
"""

import logging
from typing import List, Optional

logger = logging.getLogger("Embedder")


class Embedder:
    """
    llama-cpp-python ile GGUF embedding modeli üzerinden
    metin → dense vector dönüşümü sağlar.
    """

    def __init__(self, model_path: Optional[str], n_gpu_layers: int = 0, n_threads: int = 4, n_ctx: int = 2048):
        self.model_path = model_path
        self._llama = None

        if not model_path:
            logger.warning("Embedding model path verilmedi — semantik arama devre dışı.")
            return

        try:
            from llama_cpp import Llama
            self._llama = Llama(
                model_path=model_path,
                embedding=True,         # embedding modu
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                n_ctx=n_ctx,
                verbose=False,
            )
            logger.info(f"Embedding modeli yüklendi: {model_path}")
        except Exception as e:
            logger.error(f"Embedding modeli yüklenemedi: {e}")
            self._llama = None

    @property
    def is_available(self) -> bool:
        """Embedding engine hazır mı?"""
        return self._llama is not None

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Tek bir metin string'ini embedding vektörüne dönüştürür.
        Model yüklü değilse None döner.
        """
        if not self._llama:
            return None
        try:
            result = self._llama.embed(text)
            # llama-cpp-python sürümüne göre format farklı olabilir
            if isinstance(result, list):
                if result and isinstance(result[0], list):
                    return result[0]  # batch sonucu → ilk embedding
                return result
            return None
        except Exception as e:
            logger.error(f"Embedding hatası: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Birden fazla metin için embedding listesi döner.
        Başarısız olanlar None olarak işaretlenir.
        """
        return [self.embed(t) for t in texts]
