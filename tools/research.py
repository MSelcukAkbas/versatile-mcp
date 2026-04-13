import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP

def register_research_tools(mcp: FastMCP, search_svc, validator_svc, stackoverflow_svc, diag_svc, http_svc=None):  # noqa: E501
    @mcp.tool()
    async def validate_syntax(content: str, extension: str) -> str:
        """
        Validates code syntax using local high-performance engines (Ruff, Oxlint, Biome).
        
        Supported Extensions:
        - Python: .py
        - JavaScript: .js, .mjs, .cjs
        - TypeScript: .ts, .mts, .cts
        - Data/Markup: .json, .yaml, .yml, .xml
        
        Returns 'SUCCESS' if valid, or 'FAILURE: [Error Message]' on syntax error.
        """
        err = await diag_svc.check_tool_dependency("validate_syntax")
        if err: return err

        valid, msg = validator_svc.validate(content, extension)
        return f"SUCCESS" if valid else f"FAILURE: {msg}"

    @mcp.tool()
    async def web_search(query: str, max_results: int = 5) -> str:
        """Search the web for up-to-date information."""
        err = await diag_svc.check_tool_dependency("web_search")
        if err: return err

        results = await search_svc.search(query, max_results)
        if not results:
            return "No results found."
        return "\n".join(
            [f"### {r.get('title')}\nURL: {r.get('href')}\n{r.get('body')}\n" for r in results]
        )

    @mcp.tool()
    async def search_stackoverflow(query: str, max_results: int = 3) -> str:
        """Search Stack Overflow for technical questions and accepted answers."""
        err = await diag_svc.check_tool_dependency("search_stackoverflow")
        if err: return err

        results = await stackoverflow_svc.search(query, max_results)
        if not results:
            return "No Stack Overflow results found."
        
        output = []
        for r in results:
            if "error" in r:
                output.append(f"Error: {r['error']}")
                continue
                
            entry = [
                f"## {r['title']}",
                f"URL: {r['link']}",
                f"### Question\n{r['question_body']}",
                f"### Best Answer (Accepted)\n{r['answer_body']}",
                "---"
            ]
            output.append("\n".join(entry))
            
        return "\n\n".join(output)

    # --- Feature: Local HTTP Client ---

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
