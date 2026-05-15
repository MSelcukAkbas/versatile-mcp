import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from .sqlite import SQLiteStore
from .repository import FactRepository
from core.config import Config as BrainConfig

logger = logging.getLogger("MemoryService")


class MemoryService:
    """
    Unified service for conscious knowledge management.
    Handles storage, semantic search, and retrieval of manually committed project facts.
    (Lean v2.0 - Optimized for high reliability)
    """

    def __init__(self, data_dir: str, llama_svc=None):
        self.data_dir = data_dir
        self.llama_svc = llama_svc
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.brain_cache: Dict[tuple, tuple] = {}  # {(query, root): (timestamp, report)}

    def _get_context(self, project_root: str) -> Dict[str, Any]:
        """Initialize or retrieve the database context for a specific project."""
        if project_root in self.contexts:
            return self.contexts[project_root]

        # Prevent unbounded memory growth
        if len(self.contexts) > 50:
            self.contexts.clear()

        # Sanitize project path for directory naming
        project_id = project_root.replace("\\", "-").replace("/", "-").replace(":", "")
        mem_dir = os.path.join(self.data_dir, "projects", project_id)
        os.makedirs(mem_dir, exist_ok=True)

        db_path = os.path.join(mem_dir, "brain_memory.db")
        store = SQLiteStore(db_path)
        facts = FactRepository(db_path)

        ctx = {"store": store, "facts": facts, "project_id": project_id}
        self.contexts[project_root] = ctx
        return ctx

    def _invalidate_brain_cache(self, project_root: str):
        """Clear cached intelligence reports for a project when memory changes."""
        keys = [k for k in self.brain_cache if k[1] == project_root]
        for k in keys:
            del self.brain_cache[k]

    async def commit_knowledge(self, fact: str, project_root: str, category: str = "general") -> Dict[str, Any]:
        """
        Permanently stores a new piece of knowledge.
        Indexes the content semantically if an embedding engine is available.
        """
        ctx = self._get_context(project_root)
        fact_id = ctx["facts"].add(fact, category)

        if self.llama_svc:
            embedding = await self.llama_svc.get_embeddings(fact)
            if embedding:
                ctx["store"].add_vector(
                    f"fact_{fact_id}", 
                    fact, 
                    {"type": "fact", "category": category}, 
                    embedding
                )

        self._invalidate_brain_cache(project_root)
        return {"status": "ok", "id": fact_id, "indexed": self.llama_svc is not None}

    async def update_knowledge(self, fact_id: int, new_fact: str, project_root: str) -> Dict[str, Any]:
        """Updates the text and vector embedding of an existing knowledge entry."""
        ctx = self._get_context(project_root)
        updated = ctx["facts"].update(fact_id, new_fact)
        if not updated:
            return {"status": "error", "message": f"Knowledge ID {fact_id} not found"}

        if self.llama_svc:
            embedding = await self.llama_svc.get_embeddings(new_fact)
            if embedding:
                old_fact = ctx["facts"].get(fact_id)
                category = old_fact.get("category", "general") if old_fact else "general"
                ctx["store"].add_vector(
                    f"fact_{fact_id}", 
                    new_fact, 
                    {"type": "fact", "category": category}, 
                    embedding
                )

        self._invalidate_brain_cache(project_root)
        return {"status": "ok", "id": fact_id}

    async def delete_knowledge(self, fact_id: int, project_root: str) -> Dict[str, Any]:
        """Removes a knowledge entry from both relational and vector storage."""
        ctx = self._get_context(project_root)
        deleted = ctx["facts"].delete(fact_id)
        if not deleted:
            return {"status": "error", "message": f"Knowledge ID {fact_id} not found"}

        ctx["store"].delete_vector(f"fact_{fact_id}")
        self._invalidate_brain_cache(project_root)
        return {"status": "ok", "id": fact_id}

    async def search(self, query: str, project_root: str, n: int = None, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Performs a semantic search across stored knowledge.
        Falls back to keyword matching if embedding engine is unavailable.
        """
        n = n or BrainConfig.SEARCH_TOP_K
        ctx = self._get_context(project_root)

        if not self.llama_svc:
            facts = ctx["facts"].list(query)
            return [
                {"id": f["id"], "content": f["fact"], "score": 1.0, "type": "fact", "category": f.get("category")}
                for f in facts[:n]
            ]

        query_vec = await self.llama_svc.get_embeddings(query)
        if not query_vec:
            facts = ctx["facts"].list(query)
            return [
                {"id": f["id"], "content": f["fact"], "score": 1.0, "type": "fact", "category": f.get("category")}
                for f in facts[:n]
            ]

        results = ctx["store"].query_vector(query_vec, n=n)
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "score": r["score"],
                "type": r.get("metadata", {}).get("type", "fact"),
                "category": r.get("metadata", {}).get("category"),
            }
            for r in results
            if r["score"] >= min_score
        ]

    def list_knowledge(self, project_root: str, query: str = None, category: str = None) -> List[Dict[str, Any]]:
        """Retrieves a list of all knowledge entries, with optional filtering."""
        ctx = self._get_context(project_root)
        return ctx["facts"].list(query, category)
