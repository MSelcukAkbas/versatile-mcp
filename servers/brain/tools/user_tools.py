"""
MCP Tools — User Memory (2 tool)

user_memory_get : Kullanıcı tercihlerini sorgula (proje-scoped)
user_memory_set : Kullanıcı tercihi kaydet
"""

from typing import Optional
from fastmcp import FastMCP

from core.envelope import validate_request, make_success, make_error, EnvelopeError
from ..services.memory_service import MemoryService
from ..services.retrieval_pipeline import RetrievalPipeline


def register_user_tools(
    mcp: FastMCP,
    memory_svc: MemoryService,
    pipeline: RetrievalPipeline,
) -> None:

    @mcp.tool()
    def user_memory_get(
        project_root: str,
        query: str = None,
        n: int = 5,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to retrieve preferences, behavioral rules, or constraints explicitly set by the USER for this specific project.
        Before making subjective decisions (like formatting, style, or workflow choices), check if the user has a stored preference.

        HOW IT WORKS:
        - If `query` is provided, performs a semantic search in the 'user' namespace.
        - If `query` is None, lists the most recent user preferences.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            query: Specific preference to look for (e.g., "coding style", "commit format"). Leave empty to get general preferences.
            n: Maximum results to return (default 5).
        """
        try:
            normalized_root = validate_request(project_root, "user")
        except EnvelopeError as e:
            return make_error(str(e))

        if query:
            result = pipeline.execute(
                query=query,
                project_root=normalized_root,
                namespace="user",
                n=n,
            )
            return make_success(
                data=result,
                namespace="user",
                project_root=normalized_root,
            )
        else:
            items = memory_svc.list_active(
                project_root=normalized_root,
                namespace="user",
                limit=n,
            )
            return make_success(
                data={"items": items, "count": len(items)},
                namespace="user",
                project_root=normalized_root,
            )

    @mcp.tool()
    def user_memory_set(
        project_root: str,
        content: str,
        confidence: float = 1.0,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool when the USER explicitly tells you a rule, preference, or constraint they want you to remember for the future.
        Example triggers: "Always use tabs instead of spaces", "Don't use Tailwind in this project".

        HOW IT WORKS:
        - Stores the preference permanently in the 'user' namespace.

        RULES & CONSTRAINTS:
        - Only store things the user explicitly wants remembered or persistent workflow rules.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            content: The user's preference or rule text.
            confidence: Float between 0.0 and 1.0 (defaults to 1.0 since the user stated it).
        """
        try:
            normalized_root = validate_request(project_root, "user")
        except EnvelopeError as e:
            return make_error(str(e))

        result = memory_svc.write(
            content=content,
            project_root=normalized_root,
            namespace="user",
            confidence=confidence,
            category="user_preference",
        )

        if "error" in result:
            return make_error(result["error"], "user", normalized_root)

        return make_success(
            data=result,
            namespace="user",
            project_root=normalized_root,
            confidence=confidence,
            node_id=result.get("node_id"),
        )
