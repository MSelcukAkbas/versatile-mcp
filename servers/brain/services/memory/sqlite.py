import os
import sqlite3
import json
import numpy as np
from typing import List, Dict, Any

from core.config import Config as BrainConfig


class SQLiteStore:
    """Lite storage for vectors and structured data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db_timeout = BrainConfig.DB_TIMEOUT
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=self.db_timeout)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY, content TEXT NOT NULL,
                    metadata TEXT, embedding BLOB, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    category TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            conn.commit()

    def add_vector(self, doc_id: str, content: str, metadata: Dict[str, Any], embedding: List[float]):
        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO knowledge (id, content, metadata, embedding) VALUES (?, ?, ?, ?)",
                (doc_id, content, json.dumps(metadata), embedding_blob),
            )
            conn.commit()

    def delete_vector(self, doc_id: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM knowledge WHERE id = ?", (doc_id,))
            conn.commit()

    def delete_vectors_batch(self, doc_ids: List[str]):
        if not doc_ids:
            return
        placeholders = ",".join("?" * len(doc_ids))
        with self._connect() as conn:
            # Also handle potential chunks: delete IDs starting with doc_id + "#"
            for doc_id in doc_ids:
                conn.execute("DELETE FROM knowledge WHERE id = ? OR id LIKE ?", (doc_id, f"{doc_id}#%"))
            conn.commit()

    def delete_vectors_by_prefix(self, prefix: str):
        """Delete all vectors whose ID starts with the given prefix."""
        with self._connect() as conn:
            conn.execute("DELETE FROM knowledge WHERE id LIKE ?", (f"{prefix}%",))
            conn.commit()

    def get_all_ids(self) -> List[str]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT id FROM knowledge")
            return [row[0] for row in cursor.fetchall()]

    def get_file_mtimes(self) -> Dict[str, float]:
        """Return {doc_id: mtime} for all indexed files."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT id, metadata FROM knowledge WHERE id LIKE 'file_%'")
            result = {}
            for doc_id, meta in cursor.fetchall():
                try:
                    m = json.loads(meta) if meta else {}
                    mtime = m.get("mtime")
                    if mtime is not None:
                        result[doc_id] = mtime
                except Exception:
                    pass
            return result

    def get_stats(self) -> Dict[str, Any]:
        """Return counts and DB size."""
        with self._connect() as conn:
            vec_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            fact_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            file_count = conn.execute("SELECT COUNT(*) FROM knowledge WHERE id LIKE 'file_%'").fetchone()[0]
        try:
            db_size_kb = round(os.path.getsize(self.db_path) / 1024, 1)
        except Exception:
            db_size_kb = 0
        return {"facts": fact_count, "indexed_files": file_count, "vectors": vec_count, "db_size_kb": db_size_kb}

    def query_vector(self, query_vec: List[float], n: int = 5) -> List[Dict]:
        query_np = np.array(query_vec, dtype=np.float32)
        norm_q = np.linalg.norm(query_np)
        if norm_q == 0:
            return []

        with self._connect() as conn:
            cursor = conn.execute("SELECT id, content, metadata, embedding FROM knowledge")
            rows = cursor.fetchall()

        if not rows:
            return []

        # 1. Filter out rows without embeddings and ensure dimension match
        valid_rows = []
        embeddings = []
        query_dim = query_np.shape[0]

        for row in rows:
            if row[3]: # embedding blob
                try:
                    vec = np.frombuffer(row[3], dtype=np.float32)
                    if vec.shape[0] == query_dim:
                        valid_rows.append(row)
                        embeddings.append(vec)
                    else:
                        # Log or skip mismatched dimensions
                        continue
                except Exception:
                    continue

        if not embeddings:
            return []

        # 2. Convert to matrix and normalize
        # Matrix shape: (num_vectors, vector_dim)
        emb_matrix = np.vstack(embeddings)
        
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1.0
        norm_matrix = emb_matrix / norms

        # Normalize query vector
        norm_q_vec = query_np / norm_q if norm_q > 0 else query_np

        # 3. Compute cosine similarity in one go!
        # Result: array of similarities
        similarities = np.dot(norm_matrix, norm_q_vec)

        # 4. Build results
        results = []
        for i, row in enumerate(valid_rows):
            results.append({
                "id": row[0],
                "content": row[1],
                "metadata": json.loads(row[2]) if row[2] else {},
                "score": float(similarities[i]),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n]
