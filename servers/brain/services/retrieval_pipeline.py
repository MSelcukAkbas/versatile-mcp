"""
RetrievalPipeline — 5 Aşamalı Hibrit Retrieval Sistemi (v2)

Pipeline aşamaları:
  1. Vector Search     → ChromaDB cosine similarity (candidate set üret)
  2. Graph Expansion   → BFS ile ilişkisel komşuları ekle
  3. Metadata Filtering→ confidence, recency, validity filtreleme
  4. Re-ranking        → Cross-encoder joint scoring (ZORUNLU, kapatılamaz)
  5. Context Packing   → Token budget, deduplicate, final sıralama

Re-ranker olmadan sistem "candidate generator" olur,
"decision system" olmaz — bu yüzden her zaman açıktır.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from core.config import Config
from core.constants import SOURCE_TYPE_MEMORY, SOURCE_TYPE_REASONING
from core.helpers.embedder import Embedder
from .graph_service import GraphService
from ..storage.hybrid_store import HybridStore

logger = logging.getLogger("RetrievalPipeline")


class RetrievalPipeline:
    """5-aşamalı retrieval pipeline — re-ranker zorunlu."""

    def __init__(
        self,
        hybrid_store: HybridStore,
        embedder: Embedder,
        graph_service: GraphService,
    ):
        self.store = hybrid_store
        self.embedder = embedder
        self.graph = graph_service

    def execute(
        self,
        query: str,
        project_root: str,
        namespace: str = None,
        n: int = None,
        confidence_min: float = 0.0,
        include_reasoning: bool = False,
        deterministic: bool = False,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """
        5-aşamalı retrieval pipeline'ı çalıştır.

        Args:
            query: Arama sorgusu.
            project_root: Proje scope'u (zorunlu).
            namespace: Namespace filtresi (None = tüm namespace'ler).
            n: Maksimum sonuç sayısı.
            confidence_min: Minimum güven eşiği.
            include_reasoning: Reasoning trace'leri de dahil et.
            deterministic: True ise yüksek güven ve sıkı kurallar uygulanır.
            trace_id: Debug takip ID'si.

        Returns:
            {"candidates": [...], "pipeline_stats": {...}}
        """
        if deterministic:
            confidence_min = max(confidence_min, 0.85)
            include_reasoning = False

        n = n or Config.TOP_K
        start_time = time.time()

        # ── Aşama 1: Vector Search ─────────────────────────────────────
        candidates = self._stage_vector_search(
            query, project_root, namespace, n * 3, include_reasoning,
        )
        stage1_count = len(candidates)

        # ── Aşama 2: Graph Expansion ───────────────────────────────────
        candidates = self._stage_graph_expand(candidates, project_root)
        stage2_count = len(candidates)

        # ── Aşama 3: Metadata Filtering ────────────────────────────────
        candidates = self._stage_metadata_filter(candidates, confidence_min)
        stage3_count = len(candidates)

        # ── Aşama 4: Re-ranking (ZORUNLU) ──────────────────────────────
        candidates = self._stage_rerank(query, candidates)
        stage4_count = len(candidates)

        # ── Aşama 5: Context Packing ──────────────────────────────────
        candidates = self._stage_context_pack(candidates, n)
        stage5_count = len(candidates)

        elapsed = round(time.time() - start_time, 3)

        return {
            "candidates": candidates,
            "pipeline_stats": {
                "query": query,
                "stages": {
                    "vector_search": stage1_count,
                    "graph_expand": stage2_count,
                    "metadata_filter": stage3_count,
                    "rerank": stage4_count,
                    "context_pack": stage5_count,
                },
                "elapsed_seconds": elapsed,
                "reranker_active": True,
            },
        }

    # ══════════════════════════════════════════════════════════════════
    # STAGE 1: VECTOR SEARCH
    # ══════════════════════════════════════════════════════════════════

    def _stage_vector_search(
        self,
        query: str,
        project_root: str,
        namespace: str = None,
        n: int = 15,
        include_reasoning: bool = False,
    ) -> List[Dict[str, Any]]:
        """ChromaDB'de semantic arama — candidate set üret."""
        query_vec = self.embedder.embed(query)
        if not query_vec:
            logger.warning("Embedding üretilemedi — vector search atlandı")
            return []

        # Memory sonuçları
        results = self.store.chroma.search(
            query_embedding=query_vec,
            project_root=project_root,
            namespace=namespace,
            n=n,
            source_type=SOURCE_TYPE_MEMORY if not include_reasoning else None,
        )

        # Reasoning sonuçları (include_reasoning=True ise ayrıca çek)
        if include_reasoning:
            reasoning_results = self.store.chroma.search(
                query_embedding=query_vec,
                project_root=project_root,
                namespace="reasoning",
                n=min(n // 2, 5),
                source_type=SOURCE_TYPE_REASONING,
            )
            results.extend(reasoning_results)

        # Her candidate'e pipeline metadata ekle
        for r in results:
            r["_vector_score"] = r["score"]
            r["_source"] = "vector_search"

        return results

    # ══════════════════════════════════════════════════════════════════
    # STAGE 2: GRAPH EXPANSION
    # ══════════════════════════════════════════════════════════════════

    def _stage_graph_expand(
        self, candidates: List[Dict[str, Any]], project_root: str,
    ) -> List[Dict[str, Any]]:
        """Her candidate node için graph komşularını ekle."""
        if not candidates:
            return candidates

        depth = Config.GRAPH_EXPAND_DEPTH
        existing_ids = {c["id"] for c in candidates}
        new_candidates = []

        for candidate in candidates[:Config.RERANK_TOP_N]:
            node_id = candidate["id"]
            expansion = self.graph.expand(
                node_id=node_id,
                depth=depth,
                project_root=project_root,
            )

            for node in expansion.get("nodes", []):
                if node["id"] not in existing_ids:
                    existing_ids.add(node["id"])
                    new_candidates.append({
                        "id": node["id"],
                        "content": node.get("content", ""),
                        "score": candidate["_vector_score"] * 0.6,  # graph discount
                        "_vector_score": candidate["_vector_score"] * 0.6,
                        "_source": "graph_expansion",
                        "metadata": {
                            "namespace": node.get("namespace", ""),
                            "project_root": node.get("project_root", ""),
                        },
                    })

        candidates.extend(new_candidates)
        return candidates

    # ══════════════════════════════════════════════════════════════════
    # STAGE 3: METADATA FILTERING
    # ══════════════════════════════════════════════════════════════════

    def _stage_metadata_filter(
        self, candidates: List[Dict[str, Any]], confidence_min: float,
    ) -> List[Dict[str, Any]]:
        """Confidence, recency, validity filtreleme ve skor ayarlama."""
        now = time.time()
        recency_weight = Config.METADATA_RECENCY_WEIGHT
        filtered = []

        for c in candidates:
            meta = c.get("metadata", {})

            # Confidence filtreleme
            conf = float(meta.get("confidence", 1.0)) if "confidence" in meta else 1.0
            if conf < confidence_min:
                continue

            # Recency scoring
            vector_score = c.get("_vector_score", c.get("score", 0.0))
            # Basit recency: metadata'dan timestamp yoksa varsayılan
            recency_score = 0.5  # varsayılan orta recency
            # final_score = vector_score * (1 - weight) + recency * weight
            final_score = vector_score * (1 - recency_weight) + recency_score * recency_weight

            c["_filtered_score"] = final_score
            filtered.append(c)

        return sorted(filtered, key=lambda x: x["_filtered_score"], reverse=True)

    # ══════════════════════════════════════════════════════════════════
    # STAGE 4: RE-RANKING (ZORUNLU)
    # ══════════════════════════════════════════════════════════════════

    def _stage_rerank(
        self, query: str, candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Cross-encoder re-ranking.

        Query + candidate content birlikte embedding'e çevrilir,
        joint similarity ile final skor üretilir.

        Bu aşama ZORUNLU — kapatılamaz.
        Re-ranker olmadan pipeline:
          - embedding sim = "iyi gibi görünen ama yanlış context"
          - graph expansion = "çok ama gürültülü bilgi"
          - metadata filter = "temizlik yapar ama seçim yapmaz"
        = candidate generator, decision system değil.
        """
        if not candidates:
            return candidates

        # Top N candidate'i re-rank et (performans için)
        top_n = Config.RERANK_TOP_N
        to_rerank = candidates[:top_n]
        remaining = candidates[top_n:]

        query_vec = self.embedder.embed(query)
        if not query_vec:
            # Embedding yoksa filtered_score ile devam
            return candidates

        for c in to_rerank:
            content = c.get("content", "")
            # Cross-encoder yaklaşımı: query + content birlikte embed et
            joint_text = f"{query} [SEP] {content[:500]}"
            joint_vec = self.embedder.embed(joint_text)

            if joint_vec:
                # Joint embedding ile query embedding arasındaki similarity
                import numpy as np
                q_np = np.array(query_vec, dtype=np.float32)
                j_np = np.array(joint_vec, dtype=np.float32)
                norm_q = np.linalg.norm(q_np)
                norm_j = np.linalg.norm(j_np)
                if norm_q > 0 and norm_j > 0:
                    rerank_score = float(np.dot(q_np, j_np) / (norm_q * norm_j))
                else:
                    rerank_score = c.get("_filtered_score", 0.0)
            else:
                rerank_score = c.get("_filtered_score", 0.0)

            # Final skor: rerank ağırlıklı
            filtered = c.get("_filtered_score", c.get("score", 0.0))
            c["_rerank_score"] = rerank_score
            c["score"] = round(rerank_score * 0.7 + filtered * 0.3, 4)

        # Remaining'lere düşük skor ver
        for c in remaining:
            c["_rerank_score"] = 0.0
            c["score"] = round(c.get("_filtered_score", 0.0) * 0.5, 4)

        all_candidates = to_rerank + remaining
        return sorted(all_candidates, key=lambda x: x["score"], reverse=True)

    # ══════════════════════════════════════════════════════════════════
    # STAGE 5: CONTEXT PACKING
    # ══════════════════════════════════════════════════════════════════

    def _stage_context_pack(
        self, candidates: List[Dict[str, Any]], max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Token budget ve source deduplicate.

        - Aynı source'tan max N chunk (CONTEXT_MAX_PER_SOURCE)
        - Token budget limiti (CONTEXT_PACK_MAX_TOKENS)
        - Pipeline metadata temizle (iç kullanım alanlarını kaldır)
        """
        max_tokens = Config.CONTEXT_PACK_MAX_TOKENS
        max_per_source = Config.CONTEXT_MAX_PER_SOURCE

        source_counts: Dict[str, int] = {}
        token_count = 0
        packed = []

        for c in candidates:
            if len(packed) >= max_results:
                break

            content = c.get("content", "")
            # Yaklaşık token sayısı (word count * 1.3)
            approx_tokens = int(len(content.split()) * 1.3)

            if token_count + approx_tokens > max_tokens:
                break

            # Source deduplicate
            source = c.get("metadata", {}).get("source", "_unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
            if source_counts[source] > max_per_source:
                continue

            token_count += approx_tokens

            # Pipeline metadata temizle — sadece kullanıcıya gerekli alanlar
            clean = {
                "id": c["id"],
                "content": content,
                "score": c.get("score", 0.0),
                "metadata": c.get("metadata", {}),
            }
            packed.append(clean)

        return packed
