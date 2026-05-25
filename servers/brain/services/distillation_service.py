"""
DistillationService — Reasoning → Memory Terfi (v2)

Doğrulanmış reasoning çıktılarını (conclusions) ground truth
memory'ye terfi ettirir. Agent tetikler, otomatik değil.

Cross-Feed: Reasoning → Memory yönü.
"""

import json
import logging
from typing import Any, Dict, Optional

from core.constants import DATA_CLASS_DISTILLED
from .memory_service import MemoryService
from ..storage.hybrid_store import HybridStore

logger = logging.getLogger("DistillationService")


class DistillationService:
    """Reasoning trace'lerini verified memory'ye dönüştürme."""

    def __init__(
        self,
        hybrid_store: HybridStore,
        memory_svc: MemoryService,
    ):
        self.store = hybrid_store
        self.memory_svc = memory_svc

    def distill_session(
        self,
        session_id: str,
        project_root: str,
        target_namespace: str = "project",
        confidence: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Session'ın conclusion trace'lerini memory'ye terfi ettir.

        1) Session'ın tüm conclusion trace'lerini al
        2) Conclusion'ları birleştir → summary
        3) memory_service.write(summary, data_class="distilled")
        4) Session.distilled=1

        Returns: {"distilled_node_id": str, "conclusions_count": int}
        """
        session = self.store.sqlite.get_session(session_id)
        if not session:
            return {"error": f"Session bulunamadı: {session_id}"}

        if session.get("distilled", 0) == 1:
            return {
                "error": "Bu session zaten distill edilmiş.",
                "existing_node_id": session.get("distilled_node_id"),
            }

        # Conclusion trace'leri al
        conclusions = self.store.sqlite.get_session_traces(
            session_id, conclusions_only=True,
        )

        if not conclusions:
            return {"error": "Session'da conclusion bulunamadı. Distill edilecek bilgi yok."}

        # Summary oluştur
        summary_parts = []
        for trace in conclusions:
            summary_parts.append(trace["thought"])
        summary = "\n\n".join(summary_parts)

        # Memory'ye yaz
        result = self.memory_svc.write(
            content=summary,
            project_root=project_root,
            namespace=target_namespace,
            confidence=confidence,
            data_class=DATA_CLASS_DISTILLED,
            source=f"reasoning_session:{session_id}",
            category="distilled_reasoning",
        )

        if "error" in result:
            return result

        node_id = result["node_id"]

        # Session'ı distilled olarak işaretle
        self.store.sqlite.mark_session_distilled(session_id, node_id)

        # Reasoning -> Memory explicit links (Traceability)
        for trace in conclusions:
            self.store.sqlite.insert_edge(
                source_id=trace["id"],
                target_id=node_id,
                relation_type="derives_from",
                project_root=project_root,
                weight=1.0,
            )

        # Audit
        self.store.sqlite.insert_audit(
            operation="distill",
            target_type="reasoning_session",
            target_id=session_id,
            project_root=project_root,
            namespace=target_namespace,
            details=json.dumps({
                "distilled_node_id": node_id,
                "conclusions_count": len(conclusions),
            }),
        )

        return {
            "distilled_node_id": node_id,
            "conclusions_count": len(conclusions),
            "target_namespace": target_namespace,
            "session_id": session_id,
        }

    def distill_trace(
        self,
        trace_id: str,
        project_root: str,
        target_namespace: str = "project",
        confidence: float = 0.8,
    ) -> Dict[str, Any]:
        """Tekil trace'i memory'ye yaz (manuel distillation)."""
        trace = self.store.sqlite.get_trace(trace_id)
        if not trace:
            return {"error": f"Trace bulunamadı: {trace_id}"}

        result = self.memory_svc.write(
            content=trace["thought"],
            project_root=project_root,
            namespace=target_namespace,
            confidence=confidence,
            data_class=DATA_CLASS_DISTILLED,
            source=f"reasoning_trace:{trace_id}",
            category="distilled_reasoning",
        )

        if "error" in result:
            return result

        node_id = result["node_id"]

        # Reasoning -> Memory explicit link (Traceability)
        self.store.sqlite.insert_edge(
            source_id=trace_id,
            target_id=node_id,
            relation_type="derives_from",
            project_root=project_root,
            weight=1.0,
        )

        # Audit
        self.store.sqlite.insert_audit(
            operation="distill",
            target_type="reasoning_trace",
            target_id=trace_id,
            project_root=project_root,
            namespace=target_namespace,
            details=json.dumps({"distilled_node_id": result["node_id"]}),
        )

        return {
            "distilled_node_id": result["node_id"],
            "trace_id": trace_id,
            "target_namespace": target_namespace,
        }

    def auto_distill(self, project_root: str) -> Dict[str, Any]:
        """Tamamlanmış ama distill edilmemiş session'ları otomatik distill et."""
        sessions = self.store.sqlite.list_undistilled_sessions(project_root)
        distilled = []
        errors = []

        for session in sessions:
            result = self.distill_session(
                session_id=session["id"],
                project_root=project_root,
            )
            if "error" in result:
                errors.append({"session_id": session["id"], "error": result["error"]})
            else:
                distilled.append(result)

        return {
            "distilled_count": len(distilled),
            "error_count": len(errors),
            "distilled": distilled,
            "errors": errors,
        }
