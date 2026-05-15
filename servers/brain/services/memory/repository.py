import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timezone

from core.config import Config as BrainConfig


class FactRepository:
    """Handles structured fact storage and retrieval."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db_timeout = BrainConfig.DB_TIMEOUT

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=self.db_timeout)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, fact: str, category: str = "general") -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO facts (fact, category, created_at) VALUES (?, ?, ?)",
                (fact, category, now),
            )
            return cursor.lastrowid

    def update(self, fact_id: int, new_fact: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE facts SET fact = ?, updated_at = ? WHERE id = ?",
                (new_fact, now, fact_id),
            )
            return cursor.rowcount > 0

    def delete(self, fact_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            return cursor.rowcount > 0

    def get(self, fact_id: int) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            return dict(row) if row else None

    def list(self, query: Optional[str] = None, category: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with self._connect() as conn:
            sql = "SELECT id, fact, category, created_at, updated_at FROM facts WHERE 1=1"
            params: list = []
            if query:
                sql += " AND fact LIKE ?"
                params.append(f"%{query}%")
            if category:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
