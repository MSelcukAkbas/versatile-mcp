"""
Versatile-Memory v2 — Standart Envelope Sistemi

Agent-Native Protocol: Tüm MCP tool'ları bu modül üzerinden
request doğrulama ve response formatlama yapar.

Kurallar (Mimari.md + v2):
  - project_root zorunlu
  - namespace zorunlu (6 geçerli değer)
  - Tüm response'lar aynı JSON envelope formatında
  - İnsan açıklaması yok, sadece raw JSON
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.constants import VALID_NAMESPACES


class EnvelopeError(Exception):
    """Envelope doğrulama hatası."""
    pass


def validate_request(project_root: str, namespace: str) -> str:
    """
    Zorunlu alanları doğrula ve normalize edilmiş project_root döndür.

    Args:
        project_root: Projenin kök dizini (zorunlu).
        namespace: Memory segment (zorunlu, 6 geçerli değer).

    Returns:
        Normalize edilmiş (absolute) project_root path.

    Raises:
        EnvelopeError: Eksik veya geçersiz parametre.
    """
    if not project_root or not str(project_root).strip():
        raise EnvelopeError("project_root zorunludur. İşlem scope'u belirtilmeli.")

    if not namespace or namespace not in VALID_NAMESPACES:
        raise EnvelopeError(
            f"Geçersiz namespace: '{namespace}'. "
            f"Geçerli değerler: {sorted(VALID_NAMESPACES)}"
        )

    normalized = os.path.abspath(os.path.expanduser(str(project_root).strip()))
    return normalized


def make_response(
    status: str,
    data: Dict[str, Any],
    namespace: str,
    project_root: str,
    confidence: float = 0.0,
    graph: Optional[Dict[str, Any]] = None,
    rank: float = 0.0,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Standart MCP response envelope oluşturur.

    Mimari v2 formatı:
    {
      "id": str | null,
      "status": "success" | "error",
      "data": {},
      "meta": { timestamp, confidence, namespace, project_root },
      "graph": { nodes: [], edges: [] },
      "rank": float
    }
    """
    return {
        "id": node_id,
        "status": status,
        "data": data,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": round(confidence, 4),
            "namespace": namespace,
            "project_root": project_root,
        },
        "graph": graph or {"nodes": [], "edges": []},
        "rank": round(rank, 4),
    }


def make_success(
    data: Dict[str, Any],
    namespace: str,
    project_root: str,
    confidence: float = 0.0,
    graph: Optional[Dict[str, Any]] = None,
    rank: float = 0.0,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Başarılı response kısayolu."""
    return make_response(
        status="success",
        data=data,
        namespace=namespace,
        project_root=project_root,
        confidence=confidence,
        graph=graph,
        rank=rank,
        node_id=node_id,
    )


def make_error(
    message: str,
    namespace: str = "",
    project_root: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Hata response envelope'u."""
    return make_response(
        status="error",
        data={
            "error": message,
            **(details or {}),
        },
        namespace=namespace,
        project_root=project_root,
    )


def format_graph_hints(
    nodes: Optional[List[Dict[str, Any]]] = None,
    edges: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Graph alanı için node ve edge listelerini formatlar.

    Node format: {"id": str, "type": "memory"|"reasoning", "namespace": str, ...}
    Edge format: {"source": str, "target": str, "relation": str, ...}
    """
    return {
        "nodes": nodes or [],
        "edges": edges or [],
    }
