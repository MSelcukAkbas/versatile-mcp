"""
ChromaStore — Sadeleştirilmiş vektör depolama.

Tek koleksiyon: memory_vectors
Her kayıt:
  - id: SQLite'daki memory_nodes.id veya reasoning_traces.id ile eşleşir
  - document: metin içerik
  - embedding: vektör
  - metadata: project_root, namespace, status, data_class, source_type
"""

import logging
import os
from typing import Any, Dict, List, Optional

from core.constants import (
    CHROMA_COLLECTION_NAME,
    SOURCE_TYPE_MEMORY,
    STATUS_ACTIVE,
)

logger = logging.getLogger("ChromaStore")


class ChromaStore:
    """ChromaDB üzerinde tek koleksiyon ile vektör arama ve ekleme."""

    def __init__(self, data_dir: str):
        self.chroma_dir = os.path.join(data_dir, "chroma")
        os.makedirs(self.chroma_dir, exist_ok=True)
        self._client = None
        self._collection = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.chroma_dir)
            self._collection = self._client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB başlatıldı: {self.chroma_dir} "
                f"(koleksiyon: {CHROMA_COLLECTION_NAME}, kayıt: {self._collection.count()})"
            )
        except ImportError:
            logger.error("chromadb yüklü değil! `pip install chromadb` çalıştırın.")
            raise

    def _sanitize_meta(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """ChromaDB'nin kabul ettiği tiplere dönüştür (str/int/float/bool)."""
        result = {}
        for k, v in meta.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                result[k] = v
            else:
                result[k] = str(v)
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Write
    # ──────────────────────────────────────────────────────────────────────

    def upsert(
        self,
        node_id: str,
        content: str,
        embedding: List[float],
        project_root: str,
        namespace: str,
        status: str = STATUS_ACTIVE,
        data_class: str = "ground_truth",
        source_type: str = SOURCE_TYPE_MEMORY,
        extra_meta: Dict[str, Any] = None,
    ) -> None:
        """Vektör ekle veya güncelle."""
        meta = {
            "project_root": project_root,
            "namespace": namespace,
            "status": status,
            "data_class": data_class,
            "source_type": source_type,
        }
        if extra_meta:
            meta.update(extra_meta)

        self._collection.upsert(
            ids=[node_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[self._sanitize_meta(meta)],
        )

    def upsert_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> int:
        """
        Toplu vektör ekleme.
        items: [{"id": str, "content": str, "embedding": [...], "metadata": {...}}, ...]
        """
        if not items:
            return 0

        ids, docs, embeddings, metas = [], [], [], []
        for item in items:
            emb = item.get("embedding")
            if not emb:
                continue
            ids.append(item["id"])
            docs.append(item["content"])
            embeddings.append(emb)
            metas.append(self._sanitize_meta(item.get("metadata", {})))

        if ids:
            self._collection.upsert(
                ids=ids, documents=docs, embeddings=embeddings, metadatas=metas,
            )
        return len(ids)

    # ──────────────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────────────

    def search(
        self,
        query_embedding: List[float],
        project_root: str,
        namespace: Optional[str] = None,
        n: int = 5,
        min_score: float = 0.0,
        source_type: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Namespace-scoped semantik arama.

        Returns:
            [{"id": str, "content": str, "score": float, "metadata": dict}, ...]
        """
        # Where filtresi oluştur
        conditions = [{"project_root": project_root}]
        if namespace:
            conditions.append({"namespace": namespace})
        if not include_deprecated:
            conditions.append({"status": STATUS_ACTIVE})
        if source_type:
            conditions.append({"source_type": source_type})

        where = {"$and": conditions} if len(conditions) > 1 else conditions[0]

        collection_count = self._collection.count()
        if collection_count == 0:
            return []

        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n, collection_count),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"ChromaDB search hatası: {e}")
            return []

        results = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            # ChromaDB cosine space: distance = 1 - similarity
            score = 1.0 - distances[i]
            if score < min_score:
                continue
            results.append({
                "id": doc_id,
                "content": docs[i],
                "score": round(score, 4),
                "metadata": metas[i] if metas else {},
            })

        return sorted(results, key=lambda x: x["score"], reverse=True)

    # ──────────────────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────────────────

    def delete(self, node_id: str) -> None:
        """Tek vektör sil (deprecated node'lar aramalarda çıkmasın)."""
        try:
            self._collection.delete(ids=[node_id])
        except Exception as e:
            logger.warning(f"ChromaDB delete hatası [{node_id}]: {e}")

    def delete_batch(self, node_ids: List[str]) -> None:
        """Toplu vektör silme."""
        if node_ids:
            try:
                self._collection.delete(ids=node_ids)
            except Exception as e:
                logger.warning(f"ChromaDB batch delete hatası: {e}")

    # ──────────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Toplam vektör sayısı."""
        return self._collection.count()

    def get_stats(self) -> Dict[str, Any]:
        """Koleksiyon istatistikleri."""
        db_path = os.path.join(self.chroma_dir, "chroma.sqlite3")
        db_size_kb = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0
        return {
            "collection": CHROMA_COLLECTION_NAME,
            "record_count": self.count(),
            "db_size_kb": db_size_kb,
            "chroma_dir": self.chroma_dir,
        }
