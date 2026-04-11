import os
import sqlite3
import numpy as np
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from services.core.logger_service import setup_logger
from config.settings import resolve_paths

logger = setup_logger("MemoryService")

class LiteVectorStore:
    """A lightweight vector storage and search implementation using SQLite and Numpy."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    embedding BLOB,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Also ensure facts table exists for backward compatibility/structured data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    entity TEXT,
                    category TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add(self, doc_id: str, content: str, metadata: Dict[str, Any], embedding: List[float]):
        """Store a document and its embedding."""
        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
        metadata_json = json.dumps(metadata)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO knowledge (id, content, metadata, embedding) VALUES (?, ?, ?, ?)",
                (doc_id, content, metadata_json, embedding_blob)
            )
            conn.commit()

    def query(self, query_embedding: List[float], n_results: int = 5) -> List[Dict]:
        """Perform cosine similarity search using Numpy."""
        query_vec = np.array(query_embedding, dtype=np.float32)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, metadata, embedding FROM knowledge")
            rows = cursor.fetchall()
        
        if not rows:
            return []

        results = []
        for doc_id, content, metadata_json, embedding_blob in rows:
            doc_vec = np.frombuffer(embedding_blob, dtype=np.float32)
            
            # Cosine Similarity Calculation
            norm_q = np.linalg.norm(query_vec)
            norm_d = np.linalg.norm(doc_vec)
            
            if norm_q > 0 and norm_d > 0:
                similarity = np.dot(query_vec, doc_vec) / (norm_q * norm_d)
            else:
                similarity = 0.0
            
            results.append({
                "id": doc_id,
                "document": content,
                "metadata": json.loads(metadata_json),
                "distance": float(1.0 - similarity)  # ChromaDB style 'distance' (lower is better)
            })

        # Sort by distance (ascending)
        results.sort(key=lambda x: x["distance"])
        return results[:n_results]

class MemoryHub:
    """Represents a single memory storage unit (Unified SQLite LiteVectorStore)."""
    def __init__(self, base_dir: str, hub_name: str):
        self.base_dir = base_dir
        self.hub_name = hub_name
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Centralized SQLite path for both facts and vectors
        self.db_path = os.path.join(self.base_dir, f"{hub_name}_memory.db")
        self.store = LiteVectorStore(self.db_path)

class MemoryService:
    """Orchestrates both Global (User Habits) and Local (Project Data) memory hubs using Lite Memory."""

    def __init__(self, local_dir: str, global_dir: str, llama_svc: Optional[Any] = None):
        logger.info(f"Initializing Lite MemoryService. Local: {local_dir}, Global: {global_dir}")
        self.default_local_dir = local_dir
        self.local = MemoryHub(local_dir, "local")
        self.global_hub = MemoryHub(global_dir, "global")
        self.llama_svc = llama_svc
        self._hub_cache: Dict[str, MemoryHub] = {}  # Cache hubs per project
        self._hub_cache[local_dir] = self.local

    def _get_local_hub(self, local_memory_dir: Optional[str] = None) -> MemoryHub:
        """Get or create a MemoryHub for the given local directory, with caching."""
        if not local_memory_dir:
            return self.local

        if local_memory_dir not in self._hub_cache:
            logger.debug(f"Creating new MemoryHub for {local_memory_dir}")
            self._hub_cache[local_memory_dir] = MemoryHub(local_memory_dir, "local")

        return self._hub_cache[local_memory_dir]

    # --- Structured Fact Methods ---
    async def store_fact(self, fact: str, entity: Optional[str] = None, category: Optional[str] = "general", scope: str = "local", project_root: Optional[str] = None) -> str:
        if scope == "global":
            hub = self.global_hub
        else:
            paths = resolve_paths(project_root)
            hub = self._get_local_hub(paths["local_memory"])
        try:
            with sqlite3.connect(hub.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO facts (fact, entity, category) VALUES (?, ?, ?)",
                    (fact, entity, category)
                )
                conn.commit()
                fact_id = f"fact_{cursor.lastrowid}"

            # Auto-index for semantic search
            await self.index_text(
                text=fact,
                metadata={"type": "fact", "category": category, "entity": entity},
                doc_id=fact_id,
                scope=scope,
                project_root=project_root
            )

            return f"Fact stored and indexed in {scope} memory (ID: {fact_id})"
        except Exception as e:
            logger.error(f"store_fact fail | {e}")
            return f"Error: {str(e)}"

    def retrieve_facts(self, query: Optional[str] = None, category: Optional[str] = None, scope: str = "all", project_root: Optional[str] = None) -> List[Dict]:
        hubs = []
        if scope in ["local", "all"]:
            paths = resolve_paths(project_root)
            hubs.append(self._get_local_hub(paths["local_memory"]))
        if scope in ["global", "all"]:
            hubs.append(self.global_hub)

        all_results = []
        for hub in hubs:
            try:
                with sqlite3.connect(hub.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    sql = "SELECT * FROM facts WHERE 1=1"
                    params = []
                    if query:
                        sql += " AND fact LIKE ?"
                        params.append(f"%{query}%")
                    if category:
                        sql += " AND category = ?"
                        params.append(category)

                    sql += " ORDER BY timestamp DESC LIMIT 20"
                    cursor.execute(sql, params)
                    results = [dict(row) for row in cursor.fetchall()]
                    for r in results: r['scope'] = hub.hub_name
                    all_results.extend(results)
            except Exception as e:
                logger.error(f"Retrieve facts fail ({hub.hub_name}) | {e}")
        return all_results

    # --- Semantic (Vector) Methods ---
    async def index_text(self, text: str, metadata: Dict[str, Any], doc_id: str, scope: str = "local", project_root: Optional[str] = None) -> bool:
        if scope == "global":
            hub = self.global_hub
        else:
            paths = resolve_paths(project_root)
            hub = self._get_local_hub(paths["local_memory"])
        try:
            # Use LlamaService for local embeddings only
            if not self.llama_svc or not self.llama_svc.is_ready:
                logger.error("index_text fail | LlamaService is not ready.")
                return False
                
            embedding = self.llama_svc.get_embeddings(text)
            hub.store.add(doc_id, text, metadata, embedding)
            return True
        except Exception as e:
            logger.error(f"index_text fail | {e}")
            return False

    async def search_semantic(self, query: str, n_results: int = 5, scope: str = "all", project_root: Optional[str] = None) -> List[Dict]:
        hubs = []
        if scope in ["local", "all"]:
            paths = resolve_paths(project_root)
            hubs.append(self._get_local_hub(paths["local_memory"]))
        if scope in ["global", "all"]:
            hubs.append(self.global_hub)

        all_formatted = []
        try:
            if not self.llama_svc or not self.llama_svc.is_ready:
                logger.error("search_semantic fail | LlamaService is not ready.")
                return []
                
            query_embedding = self.llama_svc.get_embeddings(query)

            for hub in hubs:
                results = hub.store.query(query_embedding, n_results=n_results)
                for res in results:
                    res["scope"] = hub.hub_name
                    all_formatted.append(res)

            # Sort by distance (lower is better relevance)
            all_formatted.sort(key=lambda x: x['distance'])
            return all_formatted[:n_results]
        except Exception as e:
            logger.error(f"search_semantic fail | {e}")
            return []
