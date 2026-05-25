"""
MCP Tools — Graph (3 tool)

graph_expand        : BFS depth-bounded graph genişletme
graph_get_neighbors : Tek seviye komşu sorgusu
graph_link          : İki node arasında ilişki kur
"""

from typing import Any, Dict, List, Optional
from fastmcp import FastMCP

from core.envelope import validate_request, make_success, make_error, format_graph_hints, EnvelopeError
from ..services.graph_service import GraphService


def register_graph_tools(mcp: FastMCP, graph_svc: GraphService) -> None:

    @mcp.tool()
    def graph_expand(
        project_root: str,
        namespace: str,
        target_id: str,
        depth: int = 2,
        relation_types: List[str] = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to explore the network of relationships around a specific memory node.
        If you found a node via `memory_query` but need to know what else is directly or indirectly connected to it, use this.

        HOW IT WORKS:
        - Performs a Breadth-First Search (BFS) starting from `target_id`.
        - Returns all nodes and edges found up to the specified `depth`.

        RULES & CONSTRAINTS:
        - Keep `depth` small (1 or 2) to avoid pulling in the entire database and blowing up context size.
        - You can optionally filter by specific `relation_types` (e.g., ['depends_on', 'calls']).

        Args:
            project_root: The absolute path of the current project (Mandatory).
            namespace: The namespace of the target node.
            target_id: The ID of the starting node to expand from.
            depth: How many relationship hops to follow (default 2).
            relation_types: Optional list of relationship strings to filter by.
        """
        try:
            normalized_root = validate_request(project_root, namespace)
        except EnvelopeError as e:
            return make_error(str(e))

        result = graph_svc.expand(
            node_id=target_id,
            depth=depth,
            relation_types=relation_types,
            project_root=normalized_root,
        )

        graph = format_graph_hints(
            nodes=[{"id": n["id"], "type": "memory", "namespace": n.get("namespace", "")} for n in result.get("nodes", [])],
            edges=[{"source": e["source_id"], "target": e["target_id"], "relation": e["relation_type"]} for e in result.get("edges", [])],
        )

        return make_success(
            data={"nodes_count": len(result.get("nodes", [])), "edges_count": len(result.get("edges", []))},
            namespace=namespace,
            project_root=normalized_root,
            graph=graph,
            node_id=target_id,
        )

    @mcp.tool()
    def graph_get_neighbors(
        project_root: str,
        target_id: str,
        direction: str = "both",
        relation_types: List[str] = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to get ONLY the immediate (depth=1) connections to a specific node.
        Faster and more focused than `graph_expand`.

        HOW IT WORKS:
        - Returns outgoing edges, incoming edges, or both based on `direction`.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            target_id: The exact ID of the node.
            direction: Must be 'outgoing', 'incoming', or 'both' (default 'both').
            relation_types: Optional list of relationship strings to filter by.
        """
        try:
            normalized_root = validate_request(project_root, "code")
        except EnvelopeError as e:
            return make_error(str(e))

        result = graph_svc.get_neighbors(
            node_id=target_id,
            direction=direction,
            relation_types=relation_types,
        )

        return make_success(
            data=result,
            namespace="code",
            project_root=normalized_root,
            node_id=target_id,
        )

    @mcp.tool()
    def graph_link(
        project_root: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to manually create explicit relationships between two existing memory nodes.
        DO NOT use this to guess relationships; only use it when you are certain a logical link exists (e.g., Node A "depends_on" Node B).

        HOW IT WORKS:
        - Creates a directed edge from `source_id` to `target_id`.
        - If the exact edge already exists, it will update the weight instead of duplicating it.

        RULES & CONSTRAINTS:
        - `relation_type` MUST be a valid system constant (depends_on, calls, owns, derives_from, related_to, imports, implements, supersedes).

        Args:
            project_root: The absolute path of the current project (Mandatory).
            source_id: The ID of the node where the relationship starts.
            target_id: The ID of the node the relationship points to.
            relation_type: The exact string describing the relationship.
            weight: A float from 0.0 to 1.0 representing the strength of the relationship.
        """
        try:
            normalized_root = validate_request(project_root, "code")
        except EnvelopeError as e:
            return make_error(str(e))

        result = graph_svc.link(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            project_root=normalized_root,
            weight=weight,
        )

        if "error" in result:
            return make_error(result["error"], "code", normalized_root)

        return make_success(
            data=result,
            namespace="code",
            project_root=normalized_root,
            node_id=result.get("edge_id"),
        )
