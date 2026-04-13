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
        """
        Hybrid Technical Research Tool. 
        Simultaneously searches the general web and Stack Overflow for comprehensive answers.
        """
        import asyncio
        
        # Parallel execution for speed
        tasks = [
            search_svc.search(query, max_results),
            stackoverflow_svc.search(query, max_results)
        ]
        
        # Check dependencies first (informal)
        err_web = await diag_svc.check_tool_dependency("web_search")
        err_so = await diag_svc.check_tool_dependency("search_stackoverflow")
        
        web_results, so_results = await asyncio.gather(*tasks)
        
        output = []
        
        # 1. Format Stack Overflow (Technical Priority)
        if so_results and not isinstance(so_results, str):
            output.append("# 📚 STACK OVERFLOW ÇÖZÜMLERİ\n")
            for r in so_results:
                if "error" in r: continue
                output.append(f"## {r['title']}\nURL: {r['link']}\n### Answer Snippet\n{r.get('answer_body', 'No snippet available.')[:500]}...\n---\n")
        elif isinstance(so_results, str):
            output.append(f"StackOverflow Note: {so_results}")

        # 2. Format Web Results
        if web_results and not isinstance(web_results, str):
            output.append("\n# 🌐 WEB KAYNAKLARI (Dokümantasyon & Rehberler)\n")
            for r in web_results:
                output.append(f"### {r.get('title')}\nURL: {r.get('href')}\n{r.get('body')}\n")
        elif isinstance(web_results, str):
            output.append(f"Web Note: {web_results}")

        if not output:
            return "Hiçbir sonuç bulunamadı."
            
        return "\n".join(output)

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
