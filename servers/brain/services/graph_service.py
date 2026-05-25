"""
GraphService — İlişki Yönetimi (v2)

Edge CRUD + BFS Expand + Neighbor Query
SQLiteStore üzerinden çalışır.
"""

import logging
from typing import Any, Dict, List, Optional

from core.constants import VALID_RELATION_TYPES
from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger("GraphService")


class GraphService:
    """Graph tabanlı ilişki yönetimi — node'lar arası edge CRUD ve traversal."""

    def __init__(self, sqlite_store: SQLiteStore):
        self.sqlite = sqlite_store

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        project_root: str,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Edge ekle. UNIQUE constraint ihlalinde mevcut bilgiyi döner.

        Returns: {"edge_id": str | None, "created": bool}
        """
        if relation_type not in VALID_RELATION_TYPES:
            return {
                "error": f"Geçersiz relation_type: '{relation_type}'. "
                         f"Geçerli: {sorted(VALID_RELATION_TYPES)}"
            }

        edge_id = self.sqlite.insert_edge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            project_root=project_root,
            weight=weight,
        )

        if edge_id:
            # Audit
            self.sqlite.insert_audit(
                operation="link",
                target_type="edge",
                target_id=edge_id,
                project_root=project_root,
            )

        return {
            "edge_id": edge_id,
            "created": edge_id is not None,
        }

    def remove_edge(self, edge_id: str) -> Dict[str, Any]:
        """Edge sil (edge'ler versiyonlanmaz, silinebilir)."""
        removed = self.sqlite.delete_edge(edge_id)
        return {"removed": removed, "edge_id": edge_id}

    def link(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        project_root: str,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """add_edge'in kısa formu (MCP tool'dan çağrılır)."""
        return self.add_edge(source_id, target_id, relation_type, project_root, weight)

    def expand(
        self,
        node_id: str,
        depth: int = 2,
        relation_types: Optional[List[str]] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        BFS ile depth-bounded graph genişletme.

        Returns: {"nodes": [...], "edges": [...]}
        """
        return self.sqlite.expand_graph(
            start_id=node_id,
            depth=depth,
            relation_types=relation_types,
            project_root=project_root,
        )

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Tek seviye komşuları getir.

        direction: "outgoing" | "incoming" | "both"
        """
        edges = []
        if direction in ("outgoing", "both"):
            edges.extend(self.sqlite.get_edges_from(node_id))
        if direction in ("incoming", "both"):
            edges.extend(self.sqlite.get_edges_to(node_id))

        # Relation type filtreleme
        if relation_types:
            edges = [e for e in edges if e["relation_type"] in relation_types]

        # Komşu node ID'lerini topla
        neighbor_ids = set()
        for e in edges:
            neighbor_ids.add(e["source_id"])
            neighbor_ids.add(e["target_id"])
        neighbor_ids.discard(node_id)

        # Node detaylarını getir
        nodes = []
        for nid in neighbor_ids:
            node = self.sqlite.get_node(nid)
            if node:
                nodes.append(node)

        return {"nodes": nodes, "edges": edges}

    def build_subgraph(self, node_ids: List[str]) -> Dict[str, Any]:
        """Verilen node setinin iç ilişkilerini subgraph olarak döndür."""
        edges = self.sqlite.get_edges_between(node_ids)

        # Node detayları
        nodes = []
        for nid in node_ids:
            node = self.sqlite.get_node(nid)
            if node:
                nodes.append(node)

        return {"nodes": nodes, "edges": edges}
