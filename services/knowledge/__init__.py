import os
from typing import List, Dict, Any, Optional
from .storage.sqlite import SQLiteStore
from .repository.facts import FactRepository
from .retrieval.semantic import SemanticEngine
from .retrieval.hybrid import HybridResolver
from .retrieval.indexer import WorkspaceIndexer

class KnowledgeBaseService:
    """Consolidated service for memory and knowledge management."""
    
    def __init__(self, local_dir: str, global_dir: str, llama_svc: Optional[Any] = None):
        self.local_db = os.path.join(local_dir, "local_memory.db")
        os.makedirs(local_dir, exist_ok=True)
        
        self.store = SQLiteStore(self.local_db)
        self.facts = FactRepository(self.local_db)
        self.semantic = SemanticEngine(llama_svc, self.store)
        self.resolver = HybridResolver()
        self.indexer = None # Set dynamically if ignore/doc svcs are provided

    async def store_fact(self, fact: str, entity: str = None, category: str = "general"):
        fact_id = self.facts.add(fact, entity, category)
        # Auto-index for semantic search
        await self.semantic.index(fact, {"type": "fact", "category": category}, f"fact_{fact_id}")
        return f"Fact stored and indexed (ID: fact_{fact_id})"

    async def search(self, query: str, keyword_hits: List[Dict] = None, n: int = 5) -> List[Dict]:
        semantic_hits = await self.semantic.search(query, n=n)
        return self.resolver.resolve(query, keyword_hits or [], semantic_hits, n=n)

    def set_indexer(self, ignore_svc: Any, doc_svc: Any):
        self.indexer = WorkspaceIndexer(self, ignore_svc, doc_svc)

    async def index_workspace(self, project_root: str):
        if not self.indexer: return {"error": "Indexer not initialized."}
        return await self.indexer.index_workspace(project_root)
