"""
MCP Tools — Codebase (2 tool)

codebase_scan         : Proje tarama + dependency graph
codebase_update_index : Incremental güncelleme
"""

from typing import List, Optional
from fastmcp import FastMCP

from core.envelope import validate_request, make_success, make_error, EnvelopeError


def register_codebase_tools(mcp: FastMCP, codebase_scanner=None) -> None:

    @mcp.tool()
    def codebase_scan(
        project_root: str,
        extensions: List[str] = None,
        ignore_patterns: List[str] = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to perform a full semantic and relational scan of the entire codebase.
        Do this ONCE when you first encounter a new codebase to build the dependency graph and vector index.

        HOW IT WORKS:
        - Scans files, parses imports/requires, and builds a directed graph of dependencies.
        - Embeds the contents of the files into ChromaDB for semantic search.
        - Stores all this in the 'code' namespace.

        RULES & CONSTRAINTS:
        - This can take a long time on large codebases.
        - Do not run this frequently; use `codebase_update_index` for incremental updates.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            extensions: List of file extensions to include (default: ['.py']).
            ignore_patterns: List of paths or patterns to ignore (default: ['__pycache__', '.git', 'node_modules', '.venv']).
        """
        if not codebase_scanner:
            return make_error("Codebase scanner yapılandırılmamış.", "code", project_root)

        try:
            normalized_root = validate_request(project_root, "code")
        except EnvelopeError as e:
            return make_error(str(e))

        result = codebase_scanner.scan(
            project_root=normalized_root,
            extensions=extensions or [".py"],
            ignore_patterns=ignore_patterns or ["__pycache__", ".git", "node_modules", ".venv"],
        )

        if "error" in result:
            return make_error(result["error"], "code", normalized_root)

        return make_success(
            data=result,
            namespace="code",
            project_root=normalized_root,
        )

    @mcp.tool()
    def codebase_update_index(
        project_root: str,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to incrementally update the codebase index after you or the user have modified files.
        
        HOW IT WORKS:
        - Checks the last modified time (mtime) of files against the database.
        - Only re-indexes files that have changed.

        RULES & CONSTRAINTS:
        - Run this periodically during active development to keep the semantic search up to date.

        Args:
            project_root: The absolute path of the current project (Mandatory).
        """
        if not codebase_scanner:
            return make_error("Codebase scanner yapılandırılmamış.", "code", project_root)

        try:
            normalized_root = validate_request(project_root, "code")
        except EnvelopeError as e:
            return make_error(str(e))

        result = codebase_scanner.update_index(project_root=normalized_root)

        if "error" in result:
            return make_error(result["error"], "code", normalized_root)

        return make_success(
            data=result,
            namespace="code",
            project_root=normalized_root,
        )
