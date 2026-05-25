"""
SQLiteStore — Graph, Version Chain, Reasoning ve Audit tabloları.

5 tablo:
  - memory_nodes       : Ground truth bilgi birimleri
  - memory_edges       : Node'lar arası ilişkiler (graph)
  - reasoning_sessions : Düşünme oturumları
  - reasoning_traces   : Tekil düşünce adımları
  - audit_trail        : Tüm yazma işlemleri
"""

import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.constants import (
    STATUS_ACTIVE, STATUS_DEPRECATED,
    VALID_NAMESPACES, VALID_RELATION_TYPES, VALID_STATUSES,
    MEMORY_DATA_CLASSES, REASONING_DATA_CLASSES,
    SESSION_ACTIVE, SESSION_COMPLETED, SESSION_ABANDONED,
)

logger = logging.getLogger("SQLiteStore")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


class SQLiteStore:
    """SQLite tabanlı kalıcı depolama — graph, version chain, reasoning."""

    def __init__(self, data_dir: str, timeout: int = 30):
        db_dir = os.path.join(data_dir, "sqlite")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "memory.db")
        self.timeout = timeout
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _migrate(self) -> None:
        """Tabloları oluştur (idempotent)."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)
        logger.info(f"SQLite migration tamamlandı: {self.db_path}")

    # ══════════════════════════════════════════════════════════════════════
    # MEMORY NODES
    # ══════════════════════════════════════════════════════════════════════

    def insert_node(
        self,
        content: str,
        content_hash: str,
        project_root: str,
        namespace: str,
        data_class: str = "ground_truth",
        confidence: float = 1.0,
        source: str = None,
        category: str = None,
        parent_id: str = None,
        version: int = 1,
        valid_from: str = None,
        valid_until: str = None,
    ) -> str:
        """Yeni memory node ekle. ID döndürür."""
        node_id = _uuid()
        now = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO memory_nodes
                   (id, project_root, namespace, content, content_hash, data_class,
                    status, version, parent_id, confidence, source, category,
                    created_at, valid_from, valid_until, chroma_synced)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (node_id, project_root, namespace, content, content_hash,
                 data_class, STATUS_ACTIVE, version, parent_id, confidence,
                 source, category, now, valid_from or now, valid_until),
            )
        return node_id

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Tekil node getir."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memory_nodes WHERE id = ?", (node_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_node_history(self, node_id: str, max_depth: int = 50) -> List[Dict[str, Any]]:
        """Version chain: parent_id takibi ile geçmiş versiyonları getir."""
        history = []
        current_id = node_id
        depth = 0
        with self._connect() as conn:
            while current_id and depth < max_depth:
                row = conn.execute(
                    "SELECT * FROM memory_nodes WHERE id = ?", (current_id,)
                ).fetchone()
                if not row:
                    break
                node = dict(row)
                history.append(node)
                current_id = node.get("parent_id")
                depth += 1
        return history

    def deprecate_node(self, node_id: str, superseded_by: str) -> bool:
        """Node'u deprecated yap ve superseded_by ata."""
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE memory_nodes
                   SET status = ?, superseded_by = ?
                   WHERE id = ? AND status = ?""",
                (STATUS_DEPRECATED, superseded_by, node_id, STATUS_ACTIVE),
            )
            return cur.rowcount > 0

    def find_active_by_hash(
        self, content_hash: str, project_root: str, namespace: str
    ) -> Optional[Dict[str, Any]]:
        """Aynı içerik zaten var mı kontrolü (duplicate detection)."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM memory_nodes
                   WHERE content_hash = ? AND project_root = ?
                   AND namespace = ? AND status = ?
                   LIMIT 1""",
                (content_hash, project_root, namespace, STATUS_ACTIVE),
            ).fetchone()
            return dict(row) if row else None

    def list_nodes(
        self,
        project_root: str,
        namespace: str = None,
        status: str = STATUS_ACTIVE,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filtrelenmiş node listesi."""
        sql = "SELECT * FROM memory_nodes WHERE project_root = ? AND status = ?"
        params: list = [project_root, status]
        if namespace:
            sql += " AND namespace = ?"
            params.append(namespace)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_pending_sync(self) -> List[Dict[str, Any]]:
        """ChromaDB'ye senkronize edilmemiş node'lar."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_nodes WHERE chroma_synced = 0 AND status = ?",
                (STATUS_ACTIVE,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_synced(self, node_id: str) -> None:
        """Node'u ChromaDB ile senkronize edildi olarak işaretle."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE memory_nodes SET chroma_synced = 1 WHERE id = ?",
                (node_id,),
            )

    # ══════════════════════════════════════════════════════════════════════
    # MEMORY EDGES
    # ══════════════════════════════════════════════════════════════════════

    def insert_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        project_root: str,
        weight: float = 1.0,
    ) -> Optional[str]:
        """Edge ekle. Varsa ağırlığını günceller."""
        edge_id = _uuid()
        now = _now_iso()
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO memory_edges
                       (id, source_id, target_id, relation_type, project_root, weight, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (edge_id, source_id, target_id, relation_type, project_root, weight, now),
                )
            return edge_id
        except sqlite3.IntegrityError:
            logger.debug(f"Duplicate edge: {source_id} --{relation_type}--> {target_id} (Updating weight)")
            with self._connect() as conn:
                conn.execute(
                    """UPDATE memory_edges SET weight = ? 
                       WHERE source_id = ? AND target_id = ? AND relation_type = ?""",
                    (weight, source_id, target_id, relation_type)
                )
                row = conn.execute(
                    "SELECT id FROM memory_edges WHERE source_id = ? AND target_id = ? AND relation_type = ?",
                    (source_id, target_id, relation_type)
                ).fetchone()
                return row["id"] if row else None

    def get_edges_from(self, node_id: str) -> List[Dict[str, Any]]:
        """Bir node'dan çıkan tüm edge'ler."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_edges WHERE source_id = ?", (node_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_edges_to(self, node_id: str) -> List[Dict[str, Any]]:
        """Bir node'a gelen tüm edge'ler."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_edges WHERE target_id = ?", (node_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_edges_between(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Verilen node setindeki tüm iç ilişkiler (subgraph)."""
        if not node_ids:
            return []
        placeholders = ",".join("?" for _ in node_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"""SELECT * FROM memory_edges
                    WHERE source_id IN ({placeholders})
                    AND target_id IN ({placeholders})""",
                node_ids + node_ids,
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_edge(self, edge_id: str) -> bool:
        """Edge sil (edge'ler versiyonlanmaz)."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memory_edges WHERE id = ?", (edge_id,))
            return cur.rowcount > 0

    def expand_graph(
        self,
        start_id: str,
        depth: int = 2,
        relation_types: Optional[List[str]] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """BFS ile depth-bounded graph genişletme."""
        visited_nodes: Dict[str, int] = {}  # node_id → level
        all_edges: List[Dict[str, Any]] = []
        queue = [(start_id, 0)]

        with self._connect() as conn:
            while queue:
                node_id, level = queue.pop(0)
                if node_id in visited_nodes or level > depth:
                    continue
                visited_nodes[node_id] = level

                # Edge'leri al (her iki yönde)
                sql = """SELECT * FROM memory_edges
                         WHERE (source_id = ? OR target_id = ?)"""
                params: list = [node_id, node_id]

                if relation_types:
                    placeholders = ",".join("?" for _ in relation_types)
                    sql += f" AND relation_type IN ({placeholders})"
                    params.extend(relation_types)

                if project_root:
                    sql += " AND project_root = ?"
                    params.append(project_root)

                rows = conn.execute(sql, params).fetchall()
                for row in rows:
                    edge = dict(row)
                    all_edges.append(edge)
                    neighbor = edge["target_id"] if edge["source_id"] == node_id else edge["source_id"]
                    if neighbor not in visited_nodes:
                        queue.append((neighbor, level + 1))

        # Visited node'ların bilgilerini getir
        node_details = []
        if visited_nodes:
            with self._connect() as conn:
                placeholders = ",".join("?" for _ in visited_nodes)
                rows = conn.execute(
                    f"SELECT * FROM memory_nodes WHERE id IN ({placeholders})",
                    list(visited_nodes.keys()),
                ).fetchall()
                node_details = [dict(r) for r in rows]

        # Duplicate edge'leri kaldır
        seen_edges = set()
        unique_edges = []
        for e in all_edges:
            key = e["id"]
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(e)

        return {"nodes": node_details, "edges": unique_edges}

    # ══════════════════════════════════════════════════════════════════════
    # REASONING SESSIONS
    # ══════════════════════════════════════════════════════════════════════

    def insert_session(
        self, project_root: str, context: str = None
    ) -> str:
        """Yeni reasoning session başlat."""
        session_id = _uuid()
        now = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO reasoning_sessions
                   (id, project_root, started_at, status, total_thoughts, context, distilled)
                   VALUES (?, ?, ?, ?, 0, ?, 0)""",
                (session_id, project_root, now, SESSION_ACTIVE, context),
            )
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Session bilgisi."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reasoning_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def end_session(self, session_id: str, status: str = SESSION_COMPLETED) -> bool:
        """Session'ı tamamla veya terket."""
        now = _now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE reasoning_sessions
                   SET status = ?, ended_at = ?
                   WHERE id = ? AND status = ?""",
                (status, now, session_id, SESSION_ACTIVE),
            )
            return cur.rowcount > 0

    def mark_session_distilled(self, session_id: str, node_id: str) -> None:
        """Session'ı distill edildi olarak işaretle."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE reasoning_sessions
                   SET distilled = 1, distilled_node_id = ?
                   WHERE id = ?""",
                (node_id, session_id),
            )

    def list_undistilled_sessions(self, project_root: str) -> List[Dict[str, Any]]:
        """Tamamlanmış ama distill edilmemiş session'lar."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM reasoning_sessions
                   WHERE project_root = ? AND status = ? AND distilled = 0
                   ORDER BY started_at DESC""",
                (project_root, SESSION_COMPLETED),
            ).fetchall()
            return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════════════════════
    # REASONING TRACES
    # ══════════════════════════════════════════════════════════════════════

    def insert_trace(
        self,
        session_id: str,
        project_root: str,
        thought_number: int,
        thought: str,
        data_class: str = "inference",
        loop_detected: bool = False,
        similarity: float = 0.0,
        contradiction: str = None,
        progress_score: float = 0.0,
        recommendation: str = None,
        next_needed: bool = True,
        is_conclusion: bool = False,
    ) -> str:
        """Yeni reasoning trace ekle."""
        trace_id = _uuid()
        now = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO reasoning_traces
                   (id, session_id, project_root, thought_number, thought, data_class,
                    loop_detected, similarity, contradiction, progress_score,
                    recommendation, next_needed, is_conclusion, created_at, chroma_synced)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (trace_id, session_id, project_root, thought_number, thought,
                 data_class, int(loop_detected), similarity, contradiction,
                 progress_score, recommendation, int(next_needed),
                 int(is_conclusion), now),
            )
            # Session thought count güncelle
            conn.execute(
                "UPDATE reasoning_sessions SET total_thoughts = total_thoughts + 1 WHERE id = ?",
                (session_id,),
            )
        return trace_id

    def get_session_traces(
        self, session_id: str, conclusions_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Session'ın tüm trace'leri (sıralı)."""
        sql = "SELECT * FROM reasoning_traces WHERE session_id = ?"
        params: list = [session_id]
        if conclusions_only:
            sql += " AND is_conclusion = 1"
        sql += " ORDER BY thought_number ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Tekil trace."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reasoning_traces WHERE id = ?", (trace_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_pending_trace_sync(self) -> List[Dict[str, Any]]:
        """ChromaDB'ye sync edilmemiş trace'ler."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reasoning_traces WHERE chroma_synced = 0"
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_trace_synced(self, trace_id: str) -> None:
        """Trace'i senkronize edildi olarak işaretle."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE reasoning_traces SET chroma_synced = 1 WHERE id = ?",
                (trace_id,),
            )

    # ══════════════════════════════════════════════════════════════════════
    # AUDIT TRAIL
    # ══════════════════════════════════════════════════════════════════════

    def insert_audit(
        self,
        operation: str,
        target_type: str,
        target_id: str,
        project_root: str,
        namespace: str = None,
        trace_id: str = None,
        agent_confidence: float = None,
        details: str = None,
    ) -> int:
        """Audit kaydı ekle."""
        now = _now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO audit_trail
                   (operation, target_type, target_id, project_root,
                    namespace, trace_id, agent_confidence, created_at, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (operation, target_type, target_id, project_root,
                 namespace, trace_id, agent_confidence, now, details),
            )
            return cur.lastrowid


# ══════════════════════════════════════════════════════════════════════════════
# SQL SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

_SCHEMA_SQL = """
-- Memory Nodes
CREATE TABLE IF NOT EXISTS memory_nodes (
    id              TEXT PRIMARY KEY,
    project_root    TEXT NOT NULL,
    namespace       TEXT NOT NULL,
    content         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    data_class      TEXT NOT NULL DEFAULT 'ground_truth',

    status          TEXT NOT NULL DEFAULT 'active',
    superseded_by   TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    parent_id       TEXT,

    confidence      REAL NOT NULL DEFAULT 1.0,
    source          TEXT,
    category        TEXT,

    created_at      TEXT NOT NULL,
    valid_from      TEXT,
    valid_until     TEXT,

    chroma_synced   INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (superseded_by) REFERENCES memory_nodes(id),
    FOREIGN KEY (parent_id) REFERENCES memory_nodes(id)
);

CREATE INDEX IF NOT EXISTS idx_mn_project_ns ON memory_nodes(project_root, namespace);
CREATE INDEX IF NOT EXISTS idx_mn_status ON memory_nodes(status);
CREATE INDEX IF NOT EXISTS idx_mn_hash ON memory_nodes(content_hash);
CREATE INDEX IF NOT EXISTS idx_mn_parent ON memory_nodes(parent_id);

-- Memory Edges
CREATE TABLE IF NOT EXISTS memory_edges (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    relation_type   TEXT NOT NULL,
    project_root    TEXT NOT NULL,
    weight          REAL NOT NULL DEFAULT 1.0,
    created_at      TEXT NOT NULL,

    FOREIGN KEY (source_id) REFERENCES memory_nodes(id),
    FOREIGN KEY (target_id) REFERENCES memory_nodes(id),
    UNIQUE(source_id, target_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_me_source ON memory_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_me_target ON memory_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_me_project ON memory_edges(project_root);

-- Reasoning Sessions
CREATE TABLE IF NOT EXISTS reasoning_sessions (
    id              TEXT PRIMARY KEY,
    project_root    TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    total_thoughts  INTEGER NOT NULL DEFAULT 0,
    context         TEXT,
    distilled       INTEGER NOT NULL DEFAULT 0,
    distilled_node_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_rs_project ON reasoning_sessions(project_root);
CREATE INDEX IF NOT EXISTS idx_rs_status ON reasoning_sessions(status);

-- Reasoning Traces
CREATE TABLE IF NOT EXISTS reasoning_traces (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    project_root    TEXT NOT NULL,
    thought_number  INTEGER NOT NULL,
    thought         TEXT NOT NULL,
    data_class      TEXT NOT NULL DEFAULT 'inference',

    loop_detected   INTEGER NOT NULL DEFAULT 0,
    similarity      REAL DEFAULT 0.0,
    contradiction   TEXT,
    progress_score  REAL DEFAULT 0.0,
    recommendation  TEXT,

    next_needed     INTEGER NOT NULL DEFAULT 1,
    is_conclusion   INTEGER NOT NULL DEFAULT 0,

    created_at      TEXT NOT NULL,
    chroma_synced   INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (session_id) REFERENCES reasoning_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_rt_session ON reasoning_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_rt_project ON reasoning_traces(project_root);
CREATE INDEX IF NOT EXISTS idx_rt_conclusion ON reasoning_traces(is_conclusion);

-- Audit Trail
CREATE TABLE IF NOT EXISTS audit_trail (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operation       TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    project_root    TEXT NOT NULL,
    namespace       TEXT,
    trace_id        TEXT,
    agent_confidence REAL,
    created_at      TEXT NOT NULL,
    details         TEXT
);

CREATE INDEX IF NOT EXISTS idx_at_project ON audit_trail(project_root);
CREATE INDEX IF NOT EXISTS idx_at_target ON audit_trail(target_id);
"""
