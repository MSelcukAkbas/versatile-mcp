"""
ReasoningService — Düşünce Zincirleri ve Sequential Thinking (v2)

add_thought : ThinkingLoop adaptasyonu — loop detection, contradiction audit,
              progress scoring, memory context inject
trace_write : Manuel trace yazma
trace_query : Reasoning trace'lerinde semantik arama
session mgmt: start/end/get session
"""

import logging
import re
import time
from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np

from core.config import Config
from core.constants import (
    DATA_CLASS_INFERENCE, DATA_CLASS_DECISION,
    SESSION_ACTIVE, SESSION_COMPLETED,
)
from core.helpers.embedder import Embedder
from ..storage.hybrid_store import HybridStore
from .memory_service import MemoryService

logger = logging.getLogger("ReasoningService")


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """İki embedding arasında cosine similarity."""
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / (norm_a * norm_b))


class ReasoningService:
    """Sequential Thinking + Trace Memory yönetimi."""

    def __init__(
        self,
        hybrid_store: HybridStore,
        embedder: Embedder,
        memory_svc: Optional[MemoryService] = None,
    ):
        self.store = hybrid_store
        self.embedder = embedder
        self.memory_svc = memory_svc
        # RAM'deki session embedding cache (session_id → deque of embeddings)
        self._session_cache: Dict[str, deque] = {}

    # ══════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════

    def start_session(
        self, project_root: str, context: str = None,
    ) -> str:
        """Yeni reasoning session başlat."""
        session_id = self.store.sqlite.insert_session(
            project_root=project_root,
            context=context,
        )
        self._session_cache[session_id] = deque(maxlen=Config.MAX_REASONING_HISTORY)
        return session_id

    def end_session(self, session_id: str) -> Dict[str, Any]:
        """Session'ı tamamla."""
        success = self.store.sqlite.end_session(session_id, SESSION_COMPLETED)
        if session_id in self._session_cache:
            del self._session_cache[session_id]
        return {"ended": success, "session_id": session_id}

    def get_session(
        self, session_id: str, include_traces: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Session bilgisi, opsiyonel trace'lerle."""
        session = self.store.sqlite.get_session(session_id)
        if not session:
            return None
        result = {"session": session}
        if include_traces:
            result["traces"] = self.store.sqlite.get_session_traces(session_id)
        return result

    # ══════════════════════════════════════════════════════════════════
    # ADD THOUGHT (ThinkingLoop Adaptasyonu)
    # ══════════════════════════════════════════════════════════════════

    def add_thought(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        project_root: str,
        session_id: str = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Sequential thinking pipeline:
        1. Session yönetimi (yoksa otomatik oluştur)
        2. Embedding üret
        3. Loop detection (son 3 thought ile cosine similarity)
        4. Contradiction detection (negation keywords + memory audit)
        5. Progress scoring (position + novelty + conclusion boost)
        6. Memory context inject (Cross-Feed: Memory → Reasoning)
        7. Trace kaydet (SQLite + ChromaDB)
        8. Recommendation üret

        Returns: Envelope-ready intelligence report
        """
        # Session yönetimi
        if not session_id:
            session_id = self.start_session(project_root, str(context) if context else None)

        if session_id not in self._session_cache:
            self._session_cache[session_id] = deque(maxlen=Config.MAX_REASONING_HISTORY)
        history = self._session_cache[session_id]

        # 1. Embedding üret
        embedding = self.embedder.embed(thought)

        # 2. Loop Detection
        loop_info = self._detect_loop(embedding, history)

        # 3. Contradiction Detection
        contradiction = self._detect_contradiction(thought, embedding, history, project_root)

        # 4. Progress Scoring
        progress = self._calculate_progress(
            thought, thought_number, total_thoughts, embedding, history,
        )

        # 5. Memory Context Inject (Cross-Feed: Memory → Reasoning)
        memory_hits = []
        if self.memory_svc and project_root:
            try:
                memory_hits = self.store.search(
                    query=thought,
                    project_root=project_root,
                    namespace=None,  # tüm namespace'lerde ara
                    n=3,
                    min_score=Config.REASONING_MEMORY_THRESHOLD,
                )
            except Exception as e:
                logger.warning(f"Memory search failed during thinking: {e}")

        # 6. is_conclusion kontrolü
        thought_lower = thought.lower()
        is_conclusion = any(kw in thought_lower for kw in Config.CONCLUSION_KEYWORDS)
        if not next_thought_needed:
            is_conclusion = True

        # 7. Recommendation üret
        recommendation = self._generate_recommendation(
            thought, thought_number, total_thoughts, next_thought_needed,
            loop_info, contradiction, progress, memory_hits,
        )

        # 8. Trace kaydet
        intelligence = {
            "loop_detected": loop_info.get("loop_detected", False),
            "similarity": loop_info.get("similarity", 0.0),
            "contradiction": contradiction,
            "progress_score": progress.get("score", 0.0),
            "recommendation": recommendation,
        }

        data_class = DATA_CLASS_DECISION if is_conclusion else DATA_CLASS_INFERENCE

        trace_id = self.store.write_trace(
            session_id=session_id,
            project_root=project_root,
            thought_number=thought_number,
            thought=thought,
            data_class=data_class,
            intelligence=intelligence,
            next_needed=next_thought_needed,
            is_conclusion=is_conclusion,
        )

        # Explicit Memory <-> Reasoning links (Traceability)
        for hit in memory_hits:
            self.store.sqlite.insert_edge(
                source_id=trace_id,
                target_id=hit["id"],
                relation_type="derives_from",
                project_root=project_root,
                weight=1.0,
            )

        # 9. History cache güncelle
        history.append({
            "thought": thought,
            "thought_number": thought_number,
            "embedding": embedding,
        })

        return {
            "trace_id": trace_id,
            "session_id": session_id,
            "thought_number": thought_number,
            "total_thoughts": total_thoughts,
            "next_thought_needed": next_thought_needed,
            "is_conclusion": is_conclusion,
            "intelligence": {
                **loop_info,
                "stalled": progress.get("stalled", False),
                "progress_score": progress.get("score", 0.0),
                "contradiction_warning": contradiction,
                "recommendation": recommendation,
            },
            "memory_context": [
                {"id": h["id"], "content": h["content"][:200], "score": h["score"]}
                for h in memory_hits
            ],
        }

    # ══════════════════════════════════════════════════════════════════
    # TRACE OPERATIONS
    # ══════════════════════════════════════════════════════════════════

    def trace_write(
        self,
        thought: str,
        project_root: str,
        data_class: str = DATA_CLASS_INFERENCE,
        session_id: str = None,
    ) -> str:
        """Manuel trace yazma (session dışı veya bağımsız)."""
        if not session_id:
            session_id = self.start_session(project_root)

        trace_id = self.store.write_trace(
            session_id=session_id,
            project_root=project_root,
            thought_number=0,
            thought=thought,
            data_class=data_class,
        )
        return trace_id

    def trace_query(
        self, query: str, project_root: str, n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Reasoning trace'lerinde semantik arama."""
        from core.constants import SOURCE_TYPE_REASONING
        return self.store.search(
            query=query,
            project_root=project_root,
            namespace="reasoning",
            n=n,
            source_type=SOURCE_TYPE_REASONING,
        )

    # ══════════════════════════════════════════════════════════════════
    # INTELLIGENCE MODULES
    # ══════════════════════════════════════════════════════════════════

    def _detect_loop(
        self, embedding: Optional[List[float]], history: deque,
    ) -> Dict[str, Any]:
        """Semantik tekrar tespiti — son 3 thought ile cosine similarity."""
        if len(history) < 2 or not embedding:
            return {"loop_detected": False, "similarity": 0.0, "avg_similarity": 0.0, "warning": None}

        similarities = []
        for h in list(history)[-3:]:
            h_emb = h.get("embedding")
            if h_emb:
                sim = _cosine_similarity(embedding, h_emb)
                similarities.append(sim)

        if not similarities:
            return {"loop_detected": False, "similarity": 0.0, "avg_similarity": 0.0, "warning": None}

        max_sim = max(similarities)
        avg_sim = sum(similarities) / len(similarities)

        loop_detected = max_sim > Config.LOOP_SIMILARITY_THRESHOLD
        warning = None
        if loop_detected:
            warning = "Loop detected — reasoning is repeating. Try a different angle or conclude."
        elif avg_sim > Config.LOOP_WARNING_THRESHOLD:
            warning = "High repetition detected. Consider pivoting your approach."

        return {
            "loop_detected": loop_detected,
            "similarity": round(max_sim, 3),
            "avg_similarity": round(avg_sim, 3),
            "warning": warning,
        }

    def _detect_contradiction(
        self,
        thought: str,
        embedding: Optional[List[float]],
        history: deque,
        project_root: str,
    ) -> Optional[str]:
        """Negation keywords + session/memory audit ile çelişki tespiti."""
        thought_lower = thought.lower()
        has_negation = any(
            re.search(rf'\b{re.escape(kw)}\b', thought_lower)
            for kw in Config.NEGATION_KEYWORDS
        )
        if not has_negation or not embedding:
            return None

        # Session history audit
        for h in reversed(list(history)):
            h_emb = h.get("embedding")
            if not h_emb:
                continue
            sim = _cosine_similarity(embedding, h_emb)
            if sim > 0.65:
                return (
                    f"POSSIBLE CONTRADICTION with thought #{h['thought_number']} "
                    f"(topic similarity: {sim:.2f})."
                )

        # Long-term memory audit
        if self.memory_svc and project_root:
            try:
                hits = self.store.search(
                    query=thought, project_root=project_root, n=2, min_score=0.4,
                )
                for hit in hits:
                    if hit.get("score", 0) > 0.6:
                        return (
                            f"RULE VIOLATION: Contradicts stored fact: "
                            f"\"{hit['content'][:100]}...\" (Score: {hit['score']:.2f})"
                        )
            except Exception as e:
                logger.warning(f"Memory contradiction audit failed: {e}")

        return None

    def _calculate_progress(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        embedding: Optional[List[float]],
        history: deque,
    ) -> Dict[str, Any]:
        """Reasoning momentum ve stall detection."""
        position_score = thought_number / max(total_thoughts, 1)

        novelty = 1.0
        if embedding and len(history) >= 1:
            recent_sims = []
            for h in list(history)[-3:]:
                h_emb = h.get("embedding")
                if h_emb:
                    recent_sims.append(_cosine_similarity(embedding, h_emb))
            if recent_sims:
                novelty = 1.0 - (sum(recent_sims) / len(recent_sims))

        thought_lower = thought.lower()
        has_conclusion = any(kw in thought_lower for kw in Config.CONCLUSION_KEYWORDS)
        conclusion_boost = 0.2 if has_conclusion else 0.0

        score = round(min(1.0, (position_score * 0.4) + (novelty * 0.6) + conclusion_boost), 2)

        # Stall detection
        stalled = False
        if len(history) >= 3 and embedding:
            entries = list(history)[-3:]
            last_novelties = []
            for i in range(1, len(entries)):
                if entries[i].get("embedding") and entries[i - 1].get("embedding"):
                    sim = _cosine_similarity(entries[i]["embedding"], entries[i - 1]["embedding"])
                    last_novelties.append(1.0 - sim)
            if last_novelties and all(n < 0.2 for n in last_novelties):
                stalled = True

        return {"score": score, "novelty": round(novelty, 2), "stalled": stalled}

    def _generate_recommendation(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        loop_info: Dict[str, Any],
        contradiction: Optional[str],
        progress: Dict[str, Any],
        memory_hits: List[Any],
    ) -> str:
        """Bağlamsal rehberlik üret."""
        parts = []

        if loop_info.get("loop_detected"):
            parts.append("LOOP: Change approach or conclude now.")
        elif progress.get("stalled"):
            parts.append("STALLED: Try a different perspective.")

        if contradiction:
            parts.append("CONTRADICTION detected — review earlier assumptions.")

        thought_lower = thought.lower()
        has_conclusion = any(kw in thought_lower for kw in Config.CONCLUSION_KEYWORDS)
        if thought_number < total_thoughts * 0.5 and (not next_thought_needed or has_conclusion):
            parts.append("Early conclusion detected — consider if more analysis needed.")

        if thought_number >= total_thoughts and next_thought_needed:
            parts.append("Exceeding planned thoughts — wrap up soon.")

        if memory_hits:
            parts.append(f"Memory context available ({len(memory_hits)} hits).")
        elif memory_hits is not None and not memory_hits:
            parts.append("No memory context — reasoning from scratch.")

        if not parts:
            if progress.get("score", 0) > 0.7:
                return "Good progress — approaching conclusion."
            return "Continue reasoning."

        return " ".join(parts)
