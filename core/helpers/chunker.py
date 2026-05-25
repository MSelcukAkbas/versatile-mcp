"""
Chunker — Hierarchical + Sliding Window metin bölme motoru.

Strateji:
1. Önce paragraf sınırlarına göre semantic chunking dene.
2. Paragraf hâlâ büyükse sliding window ile böl.
3. Her chunk'a kaynak metadata eklenir.
"""

import re
from typing import List, Dict, Any


class Chunker:
    """
    Metni anlamlı parçalara böler.

    Args:
        chunk_size:    Hedef chunk büyüklüğü (karakter cinsinden, yaklaşık token).
        chunk_overlap: Komşu chunk'lar arasındaki örtüşme (karakter).
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Metni chunk'lara böler ve her birine metadata ekler.

        Returns:
            [{"content": str, "metadata": {...}, "chunk_index": int}, ...]
        """
        base_meta = metadata or {}
        raw_chunks = self._split(text)

        result = []
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            result.append({
                "content": chunk_text,
                "chunk_index": idx,
                "metadata": {**base_meta, "chunk_index": idx, "chunk_count": len(raw_chunks)},
            })
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _split(self, text: str) -> List[str]:
        """Önce paragrafları dene, büyük olanları sliding window ile böl."""
        paragraphs = self._split_by_paragraphs(text)
        chunks: List[str] = []

        for para in paragraphs:
            if len(para) <= self.chunk_size:
                chunks.append(para)
            else:
                # Paragraf hâlâ büyük → sliding window
                chunks.extend(self._sliding_window(para))

        return self._merge_small_chunks(chunks)

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """İki veya daha fazla newline ile ayrılmış paragraflar."""
        parts = re.split(r"\n{2,}", text)
        return [p.strip() for p in parts if p.strip()]

    def _sliding_window(self, text: str) -> List[str]:
        """Sabit boyutlu, örtüşen pencereler."""
        chunks = []
        start = 0
        step = max(1, self.chunk_size - self.chunk_overlap)

        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += step

        return chunks

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        Çok küçük chunk'ları (< chunk_size / 4) bir öncekiyle birleştir
        — vektör verimliliği için.
        """
        if not chunks:
            return chunks

        min_size = self.chunk_size // 4
        merged: List[str] = [chunks[0]]

        for chunk in chunks[1:]:
            if len(chunk) < min_size and merged:
                merged[-1] = merged[-1] + "\n\n" + chunk
            else:
                merged.append(chunk)

        return merged
