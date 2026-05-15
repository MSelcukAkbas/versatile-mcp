from typing import Optional
from fastmcp import FastMCP
from servers.master.utils.decorators import mcp_timeout

def register_research_tools(mcp: FastMCP, validator_svc, diag_svc):
    @mcp.tool()
    @mcp_timeout(seconds=15)
    async def validate_syntax(content: Optional[str] = None, extension: Optional[str] = None, file_path: Optional[str] = None) -> str:
        """
        Validates code syntax using local high-performance engines (Ruff, Oxlint, Biome).
        Ensures code quality and catches syntax errors before execution or deployment.

        Usage Modes:
        1. File Mode: Provide 'file_path'. Extension is auto-resolved.
        2. Content Mode: Provide 'content' and 'extension'.
        
        IMPORTANT: When using 'file_path', ALWAYS provide a full ABSOLUTE path (e.g., 'C:\\Users\\...') 
        to avoid file resolution errors.

        Supported Extensions:
        - Python: .py
        - JavaScript: .js, .mjs, .cjs
        - TypeScript: .ts, .mts, .cts
        - Data/Markup: .json, .yaml, .yml, .xml

        Returns 'SUCCESS' if valid, or 'FAILURE: [Error Message]' on syntax error.
        """
        err = await diag_svc.check_tool_dependency("validate_syntax")
        if err:
            return err

        if not file_path and not content:
            return "FAILURE: Either 'file_path' or 'content' must be provided."
        if content and not extension and not file_path:
            return "FAILURE: 'extension' is required when providing 'content' without a 'file_path'."

        valid, msg = validator_svc.validate(content, extension, file_path)
        return "SUCCESS" if valid else f"FAILURE: {msg}"
