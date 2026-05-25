"""
MCP Tools — Memory (memory.write, memory.update, memory.get, memory.query, memory.index)

Agent-Native Protocol: Tüm response'lar standart JSON envelope formatında.
memory.query ve memory.index → M3/M5'te eklenir.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from core.envelope import validate_request, make_success, make_error, format_graph_hints, EnvelopeError
from ..services.memory_service import MemoryService

logger = logging.getLogger("MemoryTools")


def register_memory_tools(
    mcp: FastMCP,
    memory_svc: MemoryService,
    retrieval_pipeline=None,
    index_svc=None,
) -> None:
    """Memory tool'larını MCP'ye register et."""

    @mcp.tool()
    def memory_write(
        project_root: str,
        namespace: str,
        content: str,
        confidence: float = 1.0,
        source: str = None,
        category: str = None,
        data_class: str = "ground_truth",
        edges: List[Dict[str, str]] = None,
        trace_id: str = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to permanently save NEW GROUND TRUTH facts, established architecture decisions, or verified knowledge into the system's long-term memory.
        DO NOT use this tool for temporary thoughts, guesses, inferences, or active reasoning (use `sequentialthinking_add_thought` instead).
        DO NOT use this to update existing information (use `memory_update` instead).

        HOW IT WORKS:
        - Writes data in an append-only manner (no data is ever deleted).
        - Automatically detects exact duplicates to prevent redundant entries.
        - Creates the first version of a new memory node (version=1).

        RULES & CONSTRAINTS:
        - `project_root` and `namespace` are MANDATORY.
        - `data_class` MUST be one of: 'ground_truth', 'verified', or 'distilled'. Attempting to write 'inference' or 'hypothesis' will trigger a security rule violation and fail.
        - Be precise. Store atomic, singular facts per call when possible.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            namespace: The strict domain for this memory. Must be one of: code, user, project, runtime, incident, reasoning.
            content: The exact information/fact to store.
            confidence: Float between 0.0 and 1.0 representing certainty. Defaults to 1.0 for ground truth.
            source: Where this info came from (e.g., a file path, user chat, tool output).
            category: A brief category tag (e.g., 'database_schema', 'user_preference').
            data_class: Must be 'ground_truth', 'verified', or 'distilled'. Default is 'ground_truth'.
            edges: Optional. List of dicts specifying direct links to other node IDs. Format: [{"target_id": "...", "relation_type": "..."}].
            trace_id: Optional debug/audit ID.
        """
        try:
            normalized_root = validate_request(project_root, namespace)
            from core.constants import MEMORY_DATA_CLASSES
            if data_class not in MEMORY_DATA_CLASSES:
                return make_error(f"Geçersiz data_class: {data_class}. Geçerli olanlar: {list(MEMORY_DATA_CLASSES)}")
        except EnvelopeError as e:
            return make_error(str(e))

        result = memory_svc.write(
            content=content,
            project_root=normalized_root,
            namespace=namespace,
            confidence=confidence,
            source=source,
            category=category,
            data_class=data_class,
            edges=edges,
            trace_id=trace_id,
        )

        if "error" in result:
            return make_error(result["error"], namespace, normalized_root)

        return make_success(
            data=result,
            namespace=namespace,
            project_root=normalized_root,
            confidence=confidence,
            node_id=result.get("node_id"),
        )

    @mcp.tool()
    def memory_update(
        project_root: str,
        namespace: str,
        target_id: str,
        content: str,
        confidence: float = 1.0,
        trace_id: str = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool when you need to MODIFY, CORRECT, or DEPRECATE an existing memory node.
        DO NOT use this to add completely new unrelated facts (use `memory_write` instead).

        HOW IT WORKS:
        - The system never deletes the old memory (destructive updates are forbidden).
        - Instead, it marks the old `target_id` as 'deprecated' and creates a NEW node with version+1.
        - It automatically creates a 'supersedes' graph edge from the new node to the old node to maintain full history.

        RULES & CONSTRAINTS:
        - You MUST provide the exact `target_id` of the node you are trying to update.
        - The `namespace` must match the namespace of the original node.
        - Ensure `content` contains the FULL updated text, not just a patch.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            namespace: The strict domain. Must be one of: code, user, project, runtime, incident, reasoning.
            target_id: The exact ID of the existing memory node to be updated/replaced.
            content: The complete, updated information text.
            confidence: Float between 0.0 and 1.0 representing certainty.
            trace_id: Optional debug/audit ID.
        """
        try:
            normalized_root = validate_request(project_root, namespace)
        except EnvelopeError as e:
            return make_error(str(e))

        result = memory_svc.update(
            target_id=target_id,
            new_content=content,
            project_root=normalized_root,
            namespace=namespace,
            confidence=confidence,
            trace_id=trace_id,
        )

        if "error" in result:
            return make_error(result["error"], namespace, normalized_root)

        # Graph hints: supersedes ilişkisi
        graph = format_graph_hints(
            edges=[{
                "source": result["new_id"],
                "target": result["old_id"],
                "relation": "supersedes",
            }]
        )

        return make_success(
            data=result,
            namespace=namespace,
            project_root=normalized_root,
            confidence=confidence,
            graph=graph,
            node_id=result.get("new_id"),
        )

    @mcp.tool()
    def memory_get(
        project_root: str,
        namespace: str,
        target_id: str,
        include_history: bool = False,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to fetch the EXACT, full details of a specific memory node if you already know its ID.
        DO NOT use this for searching by text or semantics (use `memory_query` instead).

        HOW IT WORKS:
        - Fetches the exact node by `target_id`.
        - Returns all connected graph edges (incoming and outgoing relationships).
        - Can optionally return the entire version history chain of how this node evolved.

        RULES & CONSTRAINTS:
        - Use this to inspect complex nodes or trace their history directly.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            namespace: The domain namespace.
            target_id: The exact node ID to retrieve.
            include_history: If True, returns previous versions (parent_id chain) of this node. Default is False.
        """
        try:
            normalized_root = validate_request(project_root, namespace)
        except EnvelopeError as e:
            return make_error(str(e))

        result = memory_svc.get(
            node_id=target_id,
            include_history=include_history,
        )

        if not result:
            return make_error(
                f"Node bulunamadı: {target_id}",
                namespace, normalized_root,
            )

        # Graph hints
        current = result.get("current", {})
        edges_data = result.get("edges", {})
        all_edges = edges_data.get("outgoing", []) + edges_data.get("incoming", [])

        graph = format_graph_hints(
            nodes=[{"id": current.get("id"), "type": "memory", "namespace": namespace}],
            edges=[
                {
                    "source": e.get("source_id"),
                    "target": e.get("target_id"),
                    "relation": e.get("relation_type"),
                }
                for e in all_edges
            ],
        )

        return make_success(
            data=result,
            namespace=namespace,
            project_root=normalized_root,
            confidence=current.get("confidence", 0.0),
            graph=graph,
            node_id=target_id,
        )

    # ── memory.query (M3: Retrieval Pipeline) ──────────────────────────

    @mcp.tool()
    def memory_query(
        project_root: str,
        namespace: str,
        query: str,
        n: int = 5,
        confidence_min: float = 0.0,
        include_reasoning: bool = False,
        deterministic: bool = False,
        trace_id: str = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to perform deep, semantic, cross-referenced searches across the system's memory.
        This is your PRIMARY TOOL for retrieving context, answering questions about the codebase, or recalling past decisions.

        HOW IT WORKS (5-Stage Pipeline):
        1. Vector Search: Finds semantic matches via ChromaDB.
        2. Graph Expansion: Automatically pulls in connected nodes (BFS) to provide surrounding context.
        3. Metadata Filtering: Filters out low-confidence or irrelevant matches.
        4. Re-ranking: Uses a mandatory cross-encoder to strictly score how well the results answer your query.
        5. Context Packing: Deduplicates and packs the best results into a token-efficient response.

        RULES & CONSTRAINTS:
        - `query` should be descriptive and semantic (e.g., "How does the auth system work?", not just "auth").
        - Set `deterministic=True` when you strictly need ONLY verified facts and exact matches without reasoning noise or fuzzy expansion.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            namespace: The specific namespace to search within (e.g., 'code', 'project'). Leave empty to search all namespaces.
            query: The natural language search query or concept to find.
            n: Maximum number of final results to return (default 5).
            confidence_min: Minimum acceptable confidence score (0.0 to 1.0).
            include_reasoning: If True, the search will also look through past reasoning traces (AI thoughts), not just ground truth.
            deterministic: If True, forces strict retrieval: bumps minimum confidence to 0.85 and explicitly excludes reasoning traces for 100% factual answers.
            trace_id: Optional debug/audit ID.
        """
        if not retrieval_pipeline:
            return make_error("Retrieval pipeline yapılandırılmamış.", namespace, project_root)

        try:
            normalized_root = validate_request(project_root, namespace)
        except EnvelopeError as e:
            return make_error(str(e))

        result = retrieval_pipeline.execute(
            query=query,
            project_root=normalized_root,
            namespace=namespace,
            n=n,
            confidence_min=confidence_min,
            include_reasoning=include_reasoning,
            deterministic=deterministic,
            trace_id=trace_id,
        )

        return make_success(
            data=result,
            namespace=namespace,
            project_root=normalized_root,
            rank=result["candidates"][0]["score"] if result.get("candidates") else 0.0,
        )

    # ── memory.index (M5: Indexing) ────────────────────────────────────

    @mcp.tool()
    def memory_index(
        project_root: str,
        namespace: str,
        path: str,
        recursive: bool = True,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool when you need to ingest ENTIRE files or directories into the memory system for semantic search later.
        Use this to read large documentation, requirements, or new code folders into the knowledge base.

        HOW IT WORKS:
        - Reads the file(s), chunks the text smartly, embeds them, and stores them as interconnected 'code' or 'project' memory nodes.

        RULES & CONSTRAINTS:
        - Supported formats: PDF, Word (.docx), Markdown (.md), TXT, and most code extensions.
        - Be careful with large directories; it may take considerable time.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            namespace: Usually 'code' for code files or 'project' for documentation/specs.
            path: Absolute path to the file or directory to index.
            recursive: If True and path is a directory, it will scan all subdirectories. Default is True.
        """
        if not index_svc:
            return make_error("Index service yapılandırılmamış.", namespace, project_root)

        try:
            normalized_root = validate_request(project_root, namespace)
        except EnvelopeError as e:
            return make_error(str(e))

        import os
        if os.path.isdir(path):
            result = index_svc.index_directory(
                directory=path,
                project_root=normalized_root,
                namespace=namespace,
                recursive=recursive,
            )
        elif os.path.isfile(path):
            result = index_svc.index_file(
                file_path=path,
                project_root=normalized_root,
                namespace=namespace,
            )
        else:
            return make_error(f"Dosya/dizin bulunamadı: {path}", namespace, normalized_root)

        if "error" in result:
            return make_error(result["error"], namespace, normalized_root)

        return make_success(
            data=result,
            namespace=namespace,
            project_root=normalized_root,
        )

