"""
HybridStore — SQLite + ChromaDB Orkestrasyon Katmanı.

Bu sınıf storage katmanının tek giriş noktasıdır.
Tüm yazma/okuma işlemleri burada koordine edilir:
  - SQLite = Truth kaynağı (node, edge, version, reasoning, audit)
  - ChromaDB = Vektör index (sadece aktif kayıtlar)

Senkronizasyon garantisi:
  1) SQLite'a yaz
  2) Embedding üret
  3) ChromaDB'ye upsert
  4) SQLite'da chroma_synced=1

Eğer 3. adım başarısız olursa, chroma_synced=0 kalır ve
sonraki sync_pending() çağrısında tekrar denenir.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from core.config import Config
from core.constants import (
    STATUS_ACTIVE, STATUS_DEPRECATED,
    RELATION_SUPERSEDES,
    SOURCE_TYPE_MEMORY, SOURCE_TYPE_REASONING,
)
from core.helpers.embedder import Embedder
from .sqlite_store import SQLiteStore
from .chroma_store import ChromaStore

logger = logging.getLogger("HybridStore")


def _content_hash(content: str) -> str:
    """SHA-256 content hash."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


class HybridStore:
    """SQLite + ChromaDB senkronize depolama orkestratörü."""

    def __init__(self, data_dir: str, embedder: Embedder, timeout: int = 30):
        self.sqlite = SQLiteStore(data_dir, timeout=timeout)
        self.chroma = ChromaStore(data_dir)
        self.embedder = embedder

    # ══════════════════════════════════════════════════════════════════════
    # MEMORY NODE OPERATIONS
    # ══════════════════════════════════════════════════════════════════════

    def write_node(
        self,
        content: str,
        project_root: str,
        namespace: str,
        data_class: str = "ground_truth",
        confidence: float = 1.0,
        source: str = None,
        category: str = None,
        edges: Optional[List[Dict[str, str]]] = None,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """
        Yeni memory node yaz.

        1) Duplicate kontrolü (content_hash)
        2) SQLite INSERT
        3) Embedding üret → ChromaDB upsert
        4) Edge'leri yaz
        5) Audit log

        Returns: {"node_id": str, "duplicate": bool, "edges_created": int}
        """
        c_hash = _content_hash(content)

        # Duplicate kontrolü
        existing = self.sqlite.find_active_by_hash(c_hash, project_root, namespace)
        if existing:
            return {
                "node_id": existing["id"],
                "duplicate": True,
                "edges_created": 0,
                "message": "Aynı içerik zaten aktif. Mevcut node ID döndürüldü.",
            }

        # 1) SQLite INSERT
        node_id = self.sqlite.insert_node(
            content=content,
            content_hash=c_hash,
            project_root=project_root,
            namespace=namespace,
            data_class=data_class,
            confidence=confidence,
            source=source,
            category=category,
        )

        # 2) Embedding → ChromaDB
        self._sync_node_to_chroma(node_id, content, project_root, namespace, data_class)

        # 3) Edge'ler
        edges_created = 0
        if edges:
            for edge_def in edges:
                eid = self.sqlite.insert_edge(
                    source_id=edge_def.get("source_id", node_id),
                    target_id=edge_def.get("target_id", node_id),
                    relation_type=edge_def.get("relation_type", "related_to"),
                    project_root=project_root,
                    weight=edge_def.get("weight", 1.0),
                )
                if eid:
                    edges_created += 1

        # 4) Audit
        self.sqlite.insert_audit(
            operation="write",
            target_type="memory_node",
            target_id=node_id,
            project_root=project_root,
            namespace=namespace,
            trace_id=trace_id,
            agent_confidence=confidence,
            details=json.dumps({"data_class": data_class, "source": source}),
        )

        return {
            "node_id": node_id,
            "duplicate": False,
            "edges_created": edges_created,
        }

    def update_node(
        self,
        target_id: str,
        new_content: str,
        project_root: str,
        namespace: str,
        confidence: float = 1.0,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """
        Version chain ile güncelleme:
        1) Eski node'u deprecate et
        2) Yeni node yaz (parent_id=eski, version=eski+1)
        3) supersedes edge
        4) ChromaDB: eski sil + yeni ekle

        Returns: {"old_id": str, "new_id": str, "version": int}
        """
        # Eski node'u bul
        old_node = self.sqlite.get_node(target_id)
        if not old_node:
            return {"error": f"Node bulunamadı: {target_id}"}
        if old_node["status"] != STATUS_ACTIVE:
            return {"error": f"Node zaten deprecated: {target_id}"}

        new_version = old_node["version"] + 1
        c_hash = _content_hash(new_content)

        # 1) Yeni node yaz
        new_id = self.sqlite.insert_node(
            content=new_content,
            content_hash=c_hash,
            project_root=project_root,
            namespace=namespace,
            data_class=old_node["data_class"],
            confidence=confidence,
            source=old_node.get("source"),
            category=old_node.get("category"),
            parent_id=target_id,
            version=new_version,
        )

        # 2) Eski node'u deprecate
        self.sqlite.deprecate_node(target_id, superseded_by=new_id)

        # 3) supersedes edge
        self.sqlite.insert_edge(
            source_id=new_id,
            target_id=target_id,
            relation_type=RELATION_SUPERSEDES,
            project_root=project_root,
        )

        # 4) ChromaDB: eski sil + yeni ekle
        self.chroma.delete(target_id)
        self._sync_node_to_chroma(new_id, new_content, project_root, namespace, old_node["data_class"])

        # 5) Audit
        self.sqlite.insert_audit(
            operation="update",
            target_type="memory_node",
            target_id=new_id,
            project_root=project_root,
            namespace=namespace,
            trace_id=trace_id,
            agent_confidence=confidence,
            details=json.dumps({"old_id": target_id, "new_version": new_version}),
        )

        return {
            "old_id": target_id,
            "new_id": new_id,
            "version": new_version,
        }

    def get_node(
        self, node_id: str, include_history: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Node getir, opsiyonel version chain ile."""
        node = self.sqlite.get_node(node_id)
        if not node:
            return None

        result = {"current": node}

        if include_history:
            history = self.sqlite.get_node_history(node_id)
            result["history"] = history[1:] if len(history) > 1 else []

        # İlişkili edge'ler
        edges_out = self.sqlite.get_edges_from(node_id)
        edges_in = self.sqlite.get_edges_to(node_id)
        result["edges"] = {
            "outgoing": edges_out,
            "incoming": edges_in,
        }

        return result

    # ══════════════════════════════════════════════════════════════════════
    # REASONING OPERATIONS
    # ══════════════════════════════════════════════════════════════════════

    def write_trace(
        self,
        session_id: str,
        project_root: str,
        thought_number: int,
        thought: str,
        data_class: str = "inference",
        intelligence: Dict[str, Any] = None,
        next_needed: bool = True,
        is_conclusion: bool = False,
    ) -> str:
        """
        Reasoning trace yaz:
        1) SQLite INSERT
        2) Embedding → ChromaDB (source_type=reasoning)

        Returns: trace_id
        """
        intel = intelligence or {}
        trace_id = self.sqlite.insert_trace(
            session_id=session_id,
            project_root=project_root,
            thought_number=thought_number,
            thought=thought,
            data_class=data_class,
            loop_detected=intel.get("loop_detected", False),
            similarity=intel.get("similarity", 0.0),
            contradiction=intel.get("contradiction"),
            progress_score=intel.get("progress_score", 0.0),
            recommendation=intel.get("recommendation"),
            next_needed=next_needed,
            is_conclusion=is_conclusion,
        )

        # ChromaDB upsert (reasoning trace'ler de aranabilir)
        embedding = self.embedder.embed(thought)
        if embedding:
            self.chroma.upsert(
                node_id=trace_id,
                content=thought,
                embedding=embedding,
                project_root=project_root,
                namespace="reasoning",
                data_class=data_class,
                source_type=SOURCE_TYPE_REASONING,
            )
            self.sqlite.mark_trace_synced(trace_id)

        # Audit
        self.sqlite.insert_audit(
            operation="thought",
            target_type="reasoning_trace",
            target_id=trace_id,
            project_root=project_root,
            namespace="reasoning",
            details=json.dumps({"session_id": session_id, "thought_number": thought_number}),
        )

        return trace_id

    # ══════════════════════════════════════════════════════════════════════
    # SEARCH (Delegating to ChromaStore)
    # ══════════════════════════════════════════════════════════════════════

    def search(
        self,
        query: str,
        project_root: str,
        namespace: str = None,
        n: int = 5,
        min_score: float = 0.0,
        source_type: str = None,
    ) -> List[Dict[str, Any]]:
        """Semantik arama (ChromaDB üzerinden)."""
        query_vec = self.embedder.embed(query)
        if not query_vec:
            return []
        return self.chroma.search(
            query_embedding=query_vec,
            project_root=project_root,
            namespace=namespace,
            n=n,
            min_score=min_score,
            source_type=source_type,
        )

    # ══════════════════════════════════════════════════════════════════════
    # SYNC
    # ══════════════════════════════════════════════════════════════════════

    def sync_pending(self) -> int:
        """chroma_synced=0 olan node ve trace'leri ChromaDB'ye senkronize et."""
        synced = 0

        # Pending nodes
        for node in self.sqlite.get_pending_sync():
            embedding = self.embedder.embed(node["content"])
            if embedding:
                self.chroma.upsert(
                    node_id=node["id"],
                    content=node["content"],
                    embedding=embedding,
                    project_root=node["project_root"],
                    namespace=node["namespace"],
                    data_class=node.get("data_class", "ground_truth"),
                    source_type=SOURCE_TYPE_MEMORY,
                )
                self.sqlite.mark_synced(node["id"])
                synced += 1

        # Pending traces
        for trace in self.sqlite.get_pending_trace_sync():
            embedding = self.embedder.embed(trace["thought"])
            if embedding:
                self.chroma.upsert(
                    node_id=trace["id"],
                    content=trace["thought"],
                    embedding=embedding,
                    project_root=trace["project_root"],
                    namespace="reasoning",
                    data_class=trace.get("data_class", "inference"),
                    source_type=SOURCE_TYPE_REASONING,
                )
                self.sqlite.mark_trace_synced(trace["id"])
                synced += 1

        if synced:
            logger.info(f"sync_pending: {synced} kayıt ChromaDB'ye senkronize edildi")
        return synced

    # ══════════════════════════════════════════════════════════════════════
    # PRIVATE
    # ══════════════════════════════════════════════════════════════════════

    def _sync_node_to_chroma(
        self, node_id: str, content: str, project_root: str,
        namespace: str, data_class: str,
    ) -> None:
        """Tek node'u ChromaDB'ye senkronize et."""
        embedding = self.embedder.embed(content)
        if embedding:
            self.chroma.upsert(
                node_id=node_id,
                content=content,
                embedding=embedding,
                project_root=project_root,
                namespace=namespace,
                data_class=data_class,
                source_type=SOURCE_TYPE_MEMORY,
            )
            self.sqlite.mark_synced(node_id)
        else:
            logger.warning(f"Embedding üretilemedi, chroma_synced=0 kalacak: {node_id}")
