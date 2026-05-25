"""
MemoryService — Ground Truth Bilgi Yönetimi (v2)

Write / Update / Get / Version Chain
Tüm işlemler HybridStore üzerinden yürütülür.
"""

import logging
from typing import Any, Dict, List, Optional

from core.constants import STATUS_ACTIVE, DATA_CLASS_GROUND_TRUTH
from ..storage.hybrid_store import HybridStore

logger = logging.getLogger("MemoryService")


class MemoryService:
    """Ground truth memory yönetimi — version chain destekli."""

    def __init__(self, hybrid_store: HybridStore):
        self.store = hybrid_store

    def write(
        self,
        content: str,
        project_root: str,
        namespace: str,
        confidence: float = 1.0,
        source: str = None,
        category: str = None,
        data_class: str = DATA_CLASS_GROUND_TRUTH,
        edges: Optional[List[Dict[str, str]]] = None,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """
        Yeni memory kaydı oluştur (append-only).

        Duplicate kontrolü yapar (content_hash).
        Version chain başlatır (version=1).
        """
        if not content or not content.strip():
            return {"error": "İçerik boş olamaz."}

        result = self.store.write_node(
            content=content.strip(),
            project_root=project_root,
            namespace=namespace,
            data_class=data_class,
            confidence=confidence,
            source=source,
            category=category,
            edges=edges,
            trace_id=trace_id,
        )
        return result

    def update(
        self,
        target_id: str,
        new_content: str,
        project_root: str,
        namespace: str,
        confidence: float = 1.0,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """
        Mevcut memory'yi güncelle (version chain).

        Eski kayıt deprecated olur, yeni kayıt version+1 ile oluşturulur.
        supersedes edge otomatik eklenir.
        """
        if not new_content or not new_content.strip():
            return {"error": "Yeni içerik boş olamaz."}

        result = self.store.update_node(
            target_id=target_id,
            new_content=new_content.strip(),
            project_root=project_root,
            namespace=namespace,
            confidence=confidence,
            trace_id=trace_id,
        )
        return result

    def get(
        self,
        node_id: str,
        include_history: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Tekil memory kaydını getir.

        include_history=True ise version chain (parent_id zinciri) de döner.
        İlişkili edge'ler her zaman döner.
        """
        return self.store.get_node(node_id, include_history=include_history)

    def list_active(
        self,
        project_root: str,
        namespace: str = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Aktif memory kayıtlarını listele."""
        return self.store.sqlite.list_nodes(
            project_root=project_root,
            namespace=namespace,
            status=STATUS_ACTIVE,
            limit=limit,
        )

    def find_by_hash(
        self,
        content_hash: str,
        project_root: str,
        namespace: str,
    ) -> Optional[Dict[str, Any]]:
        """Aynı içerik zaten var mı kontrolü."""
        return self.store.sqlite.find_active_by_hash(
            content_hash=content_hash,
            project_root=project_root,
            namespace=namespace,
        )
