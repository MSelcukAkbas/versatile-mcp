import os
import hashlib
import sqlite3
import numpy as np
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
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
            # Central Knowledge Table (Vector-ready)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    embedding BLOB,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # FTS5 Virtual Table for Hybrid Search
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                        content,
                        tokenize='porter unicode61'
                    )
                """)
            except sqlite3.OperationalError:
                logger.warning("FTS5 not supported in this SQLite build. Fallback to LIKE will be used.")

            # Facts Table (Structured Data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    entity TEXT,
                    category TEXT,
                    source TEXT DEFAULT 'assistant',
                    confidence TEXT DEFAULT 'high',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migration/Update for existing facts tables - Individual columns to avoid partial failure
            cols = [
                ("source", "TEXT DEFAULT 'assistant'"),
                ("confidence", "TEXT DEFAULT 'high'"),
                ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
            ]
            for col_name, col_def in cols:
                try:
                    cursor.execute(f"ALTER TABLE facts ADD COLUMN {col_name} {col_def}")
                except sqlite3.OperationalError:
                    pass # Column already exists
            
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
            
            # Also insert into FTS index (id corresponds to rowid logic implicitly here if we were using content table, but we use standalone)
            try:
                # Clear old index entry if exists (using content unique or just delete by text if needed, 
                # but FTS5 standalone is better managed manually here)
                cursor.execute("INSERT INTO knowledge_fts(content) VALUES (?)", (content,))
            except Exception:
                pass
                
            conn.commit()

    def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific document ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM knowledge WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

    def delete_by_prefix(self, prefix: str) -> int:
        """Delete all documents whose ID starts with the given prefix."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge WHERE id LIKE ?", (f"{prefix}%",))
            count = cursor.rowcount
            conn.commit()
            return count

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
    async def store_fact(self, fact: str, project_root: str, entity: Optional[str] = None, category: Optional[str] = "general", 
                        scope: str = "local", source: str = "assistant", confidence: str = "high") -> str:
        if scope == "global":
            hub = self.global_hub
        else:
            paths = resolve_paths(project_root)
            hub = self._get_local_hub(paths["local_memory"])
        try:
            with sqlite3.connect(hub.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO facts (fact, entity, category, source, confidence, updated_at) 
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (fact, entity, category, source, confidence)
                )
                conn.commit()
                fact_id = f"fact_{cursor.lastrowid}"

            # Auto-index for semantic search
            await self.index_text(
                text=fact,
                metadata={"type": "fact", "category": category, "entity": entity, "source": source, "confidence": confidence},
                doc_id=fact_id,
                scope=scope,
                project_root=project_root
            )

            return f"Fact stored and indexed in {scope} memory (ID: {fact_id}, Source: {source})"
        except Exception as e:
            logger.error(f"store_fact fail | {e}")
            return f"Error: {str(e)}"

    async def delete_fact(self, fact_id: str, project_root: str, scope: str = "local") -> bool:
        """Delete a fact from both SQL and Vector index."""
        if scope == "global":
            hub = self.global_hub
        else:
            paths = resolve_paths(project_root)
            hub = self._get_local_hub(paths["local_memory"])
        
        try:
            numeric_id = fact_id.replace("fact_", "")
            with sqlite3.connect(hub.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM facts WHERE id = ?", (numeric_id,))
                conn.commit()
            
            # Also delete from vector index
            await self.delete_document(fact_id, scope=scope, project_root=project_root)
            return True
        except Exception as e:
            logger.error(f"delete_fact fail | {e}")
            return False

    def retrieve_facts(self, project_root: str, query: Optional[str] = None, category: Optional[str] = None, scope: str = "all") -> List[Dict]:
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

                    sql += " ORDER BY created_at DESC LIMIT 20"
                    cursor.execute(sql, params)
                    results = [dict(row) for row in cursor.fetchall()]
                    for r in results: r['scope'] = hub.hub_name
                    all_results.extend(results)
            except Exception as e:
                logger.error(f"Retrieve facts fail ({hub.hub_name}) | {e}")
        return all_results

    async def delete_document(self, doc_id: str, project_root: str, scope: str = "local") -> int:
        """Delete a document or all its chunks (if ID is a prefix)."""
        if scope == "global":
            hub = self.global_hub
        else:
            paths = resolve_paths(project_root)
            hub = self._get_local_hub(paths["local_memory"])
        
        try:
            return hub.store.delete_by_prefix(doc_id)
        except Exception as e:
            logger.error(f"delete_document fail | {e}")
            return 0

    # --- Semantic (Vector) Methods ---
    async def index_text(self, text: str, metadata: Dict[str, Any], doc_id: str, project_root: str, scope: str = "local") -> Union[bool, str]:
        if scope == "global":
            hub = self.global_hub
        else:
            paths = resolve_paths(project_root)
            hub = self._get_local_hub(paths["local_memory"])
        try:
            # Hash check for incremental indexing
            content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            existing_meta = hub.store.get_metadata(doc_id)
            if existing_meta and existing_meta.get('content_hash') == content_hash:
                return "skipped"

            # Use LlamaService for local embeddings only
            if not self.llama_svc or not self.llama_svc.is_ready:
                logger.error("index_text fail | LlamaService is not ready.")
                return False
                
            metadata['content_hash'] = content_hash
            embedding = await self.llama_svc.get_embeddings(text)
            hub.store.add(doc_id, text, metadata, embedding)
            
            # Sync to FTS5 - Standalone insertion (metadata can be added if needed, but FTS5 best for content)
            # We don't have a direct doc_id link in standalone FTS5 easily without 'content_rowid', 
            # so we just insert the content for ranking. 
            return True
        except Exception as e:
            logger.error(f"index_text fail | {e}")
            return False

    async def search_semantic(self, query: str, project_root: str, n_results: int = 5, scope: str = "all") -> List[Dict]:
        """Hybrid Search (Vector + FTS5) across memory hubs."""
        hubs = []
        if scope in ["local", "all"]:
            paths = resolve_paths(project_root)
            hubs.append(self._get_local_hub(paths["local_memory"]))
        if scope in ["global", "all"]:
            hubs.append(self.global_hub)

        all_results = []
        try:
            if not self.llama_svc or not self.llama_svc.is_ready:
                return []
                
            query_embedding = await self.llama_svc.get_embeddings(query)

            for hub in hubs:
                # 1. Vector Results
                vector_hits = hub.store.query(query_embedding, n_results=n_results)
                
                # 2. FTS5 Keyword Results (if supported)
                fts_hits = []
                try:
                    with sqlite3.connect(hub.db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        # Simple rank-based FTS search
                        cursor.execute(
                            "SELECT content, rank FROM knowledge_fts WHERE content MATCH ? ORDER BY rank LIMIT ?",
                            (query, n_results)
                        )
                        fts_hits = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    pass # FTS5 might not be available
                
                # 3. Combine & Score (Simplified Hybrid)
                # We prioritize vector hits but boost them if content matched via FTS
                for v_hit in vector_hits:
                    v_hit["scope"] = hub.hub_name
                    # Boost if FTS found it too
                    for f_hit in fts_hits:
                        if f_hit["content"] in v_hit["document"]:
                            v_hit["distance"] *= 0.8 # Lower distance = better
                    all_results.append(v_hit)

            # Sort by boosted distance
            all_results.sort(key=lambda x: x['distance'])
            return all_results[:n_results]
        except Exception as e:
            logger.error(f"search_hybrid fail | {e}")
            return []
    async def search_hybrid(self, query: str, project_root: str, n_results: int = 5, scope: str = "all", mode: str = "hybrid", file_svc: Optional[Any] = None) -> List[Dict]:
        """
        Versatile search engine supporting three modes:
        - code: Keyword-based block search via Ripgrep.
        - memory: Conceptual-based vector search.
        - hybrid: Both merged.
        """
        results = []
        
        # 1. Mode: code or hybrid (Ripgrep)
        if mode in ["code", "hybrid"] and file_svc:
            try:
                # file_svc.search_content returns [{file, symbol, code_preview, score, ...}]
                rg_hits = file_svc.search_content(query, directory=".", context_before=2, context_after=5)
                for hit in rg_hits:
                    if "error" in hit: continue
                    results.append({
                        "source": "Keyword Search (Exact Block Match)",
                        "file": hit.get("file"),
                        "content": hit.get("code_preview"),
                        "score": hit.get("score", 0.8),
                        "metadata": {
                            "symbol": hit.get("symbol"),
                            "line_start": hit.get("line_start"),
                            "line_end": hit.get("line_end"),
                            "node_type": hit.get("node_type")
                        }
                    })
            except Exception as e:
                logger.warning(f"Hybrid Keyword search failed: {e}")

        # 2. Mode: memory or hybrid (Vector)
        if mode in ["memory", "hybrid"]:
            try:
                # self.search_semantic returns [{id, document, distance, metadata, ...}]
                vector_hits = await self.search_semantic(query, project_root, n_results=n_results, scope=scope)
                for hit in vector_hits:
                    # Normalize 'distance' to a 'score' (1 - distance)
                    score = round(1.0 - hit.get("distance", 0.5), 2)
                    results.append({
                        "source": "Vector Search (Conceptual Match)",
                        "file": hit.get("metadata", {}).get("path", "memory"),
                        "content": hit.get("document"),
                        "score": score,
                        "metadata": hit.get("metadata")
                    })
            except Exception as e:
                logger.warning(f"Hybrid Vector search failed: {e}")

        # 3. Sort & Deduplicate
        # Favor exact keyword matches if they exist
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Simple deduplication by content/file if needed, but for now we keep them to show sources
        return results[:n_results*2] if mode == "hybrid" else results[:n_results]
