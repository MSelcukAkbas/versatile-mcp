from typing import Optional, Dict, Any
import json
from fastmcp import FastMCP
from utils.decorators import mcp_timeout

def register_research_tools(mcp: FastMCP, search_svc, validator_svc, stackoverflow_svc, diag_svc, http_svc=None):  # noqa: E501
    @mcp.tool()
    @mcp_timeout(seconds=15)
    async def validate_syntax(content: Optional[str] = None, extension: Optional[str] = None, file_path: Optional[str] = None) -> str:
        """
        Validates code syntax using local high-performance engines (Ruff, Oxlint, Biome).
        
        Usage Modes:
        1. File Mode: Provide 'file_path'. Extension is auto-resolved.
        2. Content Mode: Provide 'content' and 'extension'.
        
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

    @mcp.tool()
    @mcp_timeout(seconds=20)
    async def web_search(query: str, max_results: int = 5) -> str:
        """
        Hybrid Technical Research Tool.
        Simultaneously searches the general web and Stack Overflow for comprehensive answers.
        """
        # Minimal wrapper to avoid serialization issues
        try:
            # Ensure web_results and so_results are properly isolated
            web_text = ""
            so_text = ""

            try:
                web_results = await search_svc.search(query, max_results)
                if web_results and isinstance(web_results, list):
                    web_text = "WEB RESULTS:\n"
                    for idx, item in enumerate(web_results):
                        if idx >= 2:
                            break
                        if isinstance(item, dict) and "error" not in item:
                            web_text += f"- {item.get('title', 'Title')}\n"
                            web_text += f"  {item.get('href', 'No URL')}\n\n"
            except Exception as e:
                web_text = f"Web search error: {str(e)}\n"

            try:
                # StackOverflowService.search() is SYNC (not async), despite tool being async
                so_results = stackoverflow_svc.search(query, max_results)
                if so_results and isinstance(so_results, list):
                    so_text = "\nSTACK OVERFLOW RESULTS:\n"
                    for idx, item in enumerate(so_results):
                        if idx >= 2:
                            break
                        if isinstance(item, dict) and "error" not in item:
                            so_text += f"- {item.get('title', 'Title')}\n"
                            so_text += f"  {item.get('link', 'No link')}\n\n"
            except Exception as e:
                so_text = f"StackOverflow error: {str(e)}\n"

            combined = web_text + so_text
            return combined if combined.strip() else f"No results for query: {query}"

        except Exception as e:
            return f"Search failed: {str(e)}"

    @mcp.tool()
    async def http_request(
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Make an HTTP request to a local or private-network endpoint.
        Only localhost and RFC-1918 private IPs are allowed.
        method: GET | POST | PUT | DELETE | PATCH
        """
        if http_svc is None:
            return "HttpClientService is not available."
        result = await http_svc.request(method, url, headers=headers, body=body,
                                        params=params, timeout=timeout)
        if "error" in result:
            return f"Error: {result['error']}"
        latency = f"  ({result['latency_ms']} ms)" if result.get("latency_ms") else ""
        return (
            f"Status: {result['status_code']}{latency}\n"
            f"Headers: {json.dumps(dict(result['headers']), indent=2)}\n"
            f"Body:\n{result['body']}"
        )
