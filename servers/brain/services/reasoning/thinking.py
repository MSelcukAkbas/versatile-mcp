import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from collections import deque

from core.config import Config as BrainConfig

logger = logging.getLogger("ThinkingLoop")


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / (norm_a * norm_b))


class ThinkingLoop:
    """
    Advanced reasoning engine with semantic awareness and logical auditing.
    
    Features:
    - Semantic loop detection (embedding-based)
    - Contradiction auditing against local history and long-term memory
    - Progress and momentum scoring
    - Automatic conclusion archival to 'Conscious Memory'
    """

    def __init__(self, max_history: int = None, memory_svc=None, llama_svc=None):
        self.max_history = max_history or BrainConfig.MAX_REASONING_HISTORY
        self.memory_svc = memory_svc
        self.llama_svc = llama_svc
        self.sessions: Dict[str, Dict[str, Any]] = {}  # session_id → {history, context, project_root}

    def _get_session(self, session_id: str = "default") -> Dict[str, Any]:
        """Retrieve or initialize a reasoning session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": deque(maxlen=self.max_history),
                "context": None,
                "project_root": None
            }
        return self.sessions[session_id]

    def clear_session(self, session_id: str = None):
        """Clear reasoning history and context for a specific session or all sessions."""
        if session_id:
            self.sessions.pop(session_id, None)
        else:
            self.sessions.clear()

    async def add_thought(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        context: Optional[dict] = None,
        project_root: Optional[str] = None,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Executes the full reasoning pipeline for a single thought.
        Returns a structured report with semantic analysis and guidance.
        """
        session = self._get_session(session_id)
        history = session["history"]
        
        # Sync session state
        if context:
            session["context"] = context
        if project_root:
            session["project_root"] = project_root
            
        active_context = session["context"]
        active_root = session["project_root"]

        # 1. Generate embedding for semantic analysis
        embedding = None
        if self.llama_svc:
            embedding = await self.llama_svc.get_embeddings(thought)

        # 2. Audit: Loop Detection
        loop_info = self._detect_loop(embedding, history)

        # 3. Audit: Contradiction Detection
        contradiction = await self._detect_contradiction(thought, embedding, history, active_root)

        # 4. Memory Integration: Context Retrieval
        memory_hits = []
        search_suggestion = None
        if self.memory_svc and active_root:
            try:
                memory_hits = await self.memory_svc.search(
                    thought, 
                    active_root, 
                    n=3, 
                    min_score=BrainConfig.REASONING_MEMORY_THRESHOLD
                )
                if not memory_hits:
                    search_suggestion = "No relevant memory found. Consider commit_knowledge to save key insights for later."
            except Exception as e:
                logger.warning(f"Memory search failed during thinking: {e}")

        # 5. Momentum Analysis
        progress = self._calculate_progress(thought, thought_number, total_thoughts, embedding, history)

        # 6. Strategic Guidance
        recommendation = self._generate_recommendation(
            thought, thought_number, total_thoughts, next_thought_needed,
            loop_info, contradiction, progress, memory_hits
        )

        # 7. Record History
        history.append({
            "thought": thought,
            "thought_number": thought_number,
            "embedding": embedding,
            "has_context": active_context is not None,
        })

        # 8. Archival: Auto-save conclusion to memory
        saved_to_memory = False
        if not next_thought_needed and self.memory_svc and active_root:
            try:
                await self.memory_svc.commit_knowledge(thought, active_root, category="reasoning")
                saved_to_memory = True
            except Exception as e:
                logger.warning(f"Failed to auto-save reasoning conclusion: {e}")

        return {
            "status": "success",
            "data": {
                "thought": thought,
                "thought_number": thought_number,
                "total_thoughts": total_thoughts,
                "next_thought_needed": next_thought_needed,
                "context_received": context is not None,
                "using_sticky_context": context is None and active_context is not None
            },
            "memory_context": memory_hits,
            "intelligence": {
                **loop_info,
                "stalled": progress.get("stalled", False),
                "progress_score": progress.get("score", 0.0),
                "contradiction_warning": contradiction,
                "search_suggestion": search_suggestion,
                "recommendation": recommendation,
                "completion_estimate": f"{max(0, total_thoughts - thought_number)} more thoughts needed",
                "saved_to_memory": saved_to_memory,
            },
        }

    def _detect_loop(self, embedding: Optional[List[float]], history: deque) -> Dict[str, Any]:
        """Analyzes semantic repetition between the current thought and history."""
        if len(history) < 2 or not embedding:
            return {"loop_detected": False, "similarity": 0.0, "avg_similarity": 0.0, "warning": None}

        similarities = []
        for h in list(history)[-3:]:
            h_emb = h.get("embedding")
            if h_emb:
                sim = cosine_similarity(embedding, h_emb)
                similarities.append(sim)

        if not similarities:
            return {"loop_detected": False, "similarity": 0.0, "avg_similarity": 0.0, "warning": None}

        max_sim = max(similarities)
        avg_sim = sum(similarities) / len(similarities)

        loop_detected = max_sim > BrainConfig.LOOP_SIMILARITY_THRESHOLD
        warning = None
        if loop_detected:
            warning = "Loop detected — reasoning is repeating. Try a different angle or conclude."
        elif avg_sim > BrainConfig.LOOP_WARNING_THRESHOLD:
            warning = "High repetition detected. Consider pivoting your approach."

        return {
            "loop_detected": loop_detected,
            "similarity": round(max_sim, 3),
            "avg_similarity": round(avg_sim, 3),
            "warning": warning,
        }

    async def _detect_contradiction(
        self, thought: str, embedding: Optional[List[float]], history: deque, project_root: Optional[str] = None
    ) -> Optional[str]:
        """Audits current thought against history and memory for logical contradictions."""
        thought_lower = thought.lower()

        # Check for negation indicators
        has_negation = any(re.search(rf'\b{re.escape(kw)}\b', thought_lower) for kw in BrainConfig.NEGATION_KEYWORDS)
        if not has_negation or not embedding:
            return None

        # 1. Audit Session History
        for h in reversed(list(history)):
            h_emb = h.get("embedding")
            if not h_emb:
                continue
            sim = cosine_similarity(embedding, h_emb)
            if sim > 0.65:
                return f"POSSIBLE CONTRADICTION with your previous thought #{h['thought_number']} (topic similarity: {sim:.2f})."

        # 2. Audit Long-term Memory
        if self.memory_svc and project_root:
            try:
                hits = await self.memory_svc.search(thought, project_root, n=2, min_score=0.4)
                for hit in hits:
                    if hit.get("score", 0) > 0.6:
                        return (
                            f"RULE VIOLATION: Current thought might contradict a stored project fact: "
                            f"\"{hit['content'][:100]}...\" (Confidence: {hit['score']:.2f})"
                        )
            except Exception as e:
                logger.warning(f"Memory contradiction audit failed: {e}")

        return None

    def _calculate_progress(
        self, thought: str, thought_number: int, total_thoughts: int,
        embedding: Optional[List[float]], history: deque
    ) -> Dict[str, Any]:
        """Calculates reasoning momentum and detects stalls."""
        position_score = thought_number / max(total_thoughts, 1)

        novelty = 1.0
        if embedding and len(history) >= 1:
            recent_sims = []
            for h in list(history)[-3:]:
                h_emb = h.get("embedding")
                if h_emb:
                    recent_sims.append(cosine_similarity(embedding, h_emb))
            if recent_sims:
                novelty = 1.0 - (sum(recent_sims) / len(recent_sims))

        thought_lower = thought.lower()
        has_conclusion = any(kw in thought_lower for kw in BrainConfig.CONCLUSION_KEYWORDS)
        conclusion_boost = 0.2 if has_conclusion else 0.0

        score = round(min(1.0, (position_score * 0.4) + (novelty * 0.6) + conclusion_boost), 2)

        # Stall detection logic
        stalled = False
        if len(history) >= 3 and embedding:
            last_three_novelties = []
            entries = list(history)[-3:]
            for i, h in enumerate(entries):
                if i > 0 and entries[i - 1].get("embedding") and h.get("embedding"):
                    sim = cosine_similarity(h["embedding"], entries[i - 1]["embedding"])
                    last_three_novelties.append(1.0 - sim)
            if last_three_novelties and all(n < 0.2 for n in last_three_novelties):
                stalled = True

        return {"score": score, "novelty": round(novelty, 2), "stalled": stalled}

    def _generate_recommendation(
        self, thought: str, thought_number: int, total_thoughts: int, next_thought_needed: bool,
        loop_info: Dict[str, Any], contradiction: Optional[str], progress: Dict[str, Any], memory_hits: List[Any]
    ) -> str:
        """Generates contextual guidance for the next reasoning step."""
        parts = []

        if loop_info.get("loop_detected"):
            parts.append("LOOP: Change approach or conclude now.")
        elif progress.get("stalled"):
            parts.append("STALLED: Try a different perspective.")

        if contradiction:
            parts.append("CONTRADICTION detected — review earlier assumptions.")

        thought_lower = thought.lower()
        has_conclusion = any(kw in thought_lower for kw in BrainConfig.CONCLUSION_KEYWORDS)
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
