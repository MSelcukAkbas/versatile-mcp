"""
MCP Tools — Project Memory (2 tool)

project_memory_get : Mimari kararları sorgula
project_memory_set : Mimari karar/tasarım notu kaydet
"""

from typing import Optional
from fastmcp import FastMCP

from core.envelope import validate_request, make_success, make_error, EnvelopeError
from ..services.memory_service import MemoryService
from ..services.retrieval_pipeline import RetrievalPipeline


def register_project_tools(
    mcp: FastMCP,
    memory_svc: MemoryService,
    pipeline: RetrievalPipeline,
) -> None:

    @mcp.tool()
    def project_memory_get(
        project_root: str,
        query: str = None,
        n: int = 5,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to recall architectural decisions, design patterns, and system-wide rules specific to this project.
        Before adding new dependencies, changing architecture, or creating new modules, query this tool to ensure you align with established project guidelines.

        HOW IT WORKS:
        - If `query` is provided, performs a semantic search in the 'project' namespace.
        - If `query` is None, lists the most recent project-wide architectural decisions.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            query: Specific architectural concept to look for (e.g., "state management", "database tech stack").
            n: Maximum results to return (default 5).
        """
        try:
            normalized_root = validate_request(project_root, "project")
        except EnvelopeError as e:
            return make_error(str(e))

        if query:
            result = pipeline.execute(
                query=query,
                project_root=normalized_root,
                namespace="project",
                n=n,
            )
            return make_success(
                data=result,
                namespace="project",
                project_root=normalized_root,
            )
        else:
            items = memory_svc.list_active(
                project_root=normalized_root,
                namespace="project",
                limit=n,
            )
            return make_success(
                data={"items": items, "count": len(items)},
                namespace="project",
                project_root=normalized_root,
            )

    @mcp.tool()
    def project_memory_set(
        project_root: str,
        content: str,
        confidence: float = 1.0,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to document a major architectural decision (ADR), technical stack choice, or project-wide rule you have established.
        DO NOT use this for small code snippets; use it for high-level system rules.

        HOW IT WORKS:
        - Stores the decision permanently in the 'project' namespace.

        RULES & CONSTRAINTS:
        - Ensure the content clearly states the decision, the context, and the consequences.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            content: The detailed text of the architectural decision.
            confidence: Float between 0.0 and 1.0 representing how firm this decision is.
        """
        try:
            normalized_root = validate_request(project_root, "project")
        except EnvelopeError as e:
            return make_error(str(e))

        result = memory_svc.write(
            content=content,
            project_root=normalized_root,
            namespace="project",
            confidence=confidence,
            category="architecture_decision",
        )

        if "error" in result:
            return make_error(result["error"], "project", normalized_root)

        return make_success(
            data=result,
            namespace="project",
            project_root=normalized_root,
            confidence=confidence,
            node_id=result.get("node_id"),
        )
