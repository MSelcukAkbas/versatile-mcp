from fastmcp import FastMCP

def register_research_tools(mcp: FastMCP, search_svc, validator_svc, stackoverflow_svc):
    @mcp.tool()
    async def validate_syntax(content: str, extension: str) -> str:
        """
        Validate code syntax locally without any AI. 
        Supports: json, yaml, py, xml, js, ts, mjs, cjs, mts, cts.
        """
        valid, msg = validator_svc.validate(content, extension)
        return f"SUCCESS" if valid else f"FAILURE: {msg}"

    @mcp.tool()
    async def web_search(query: str, max_results: int = 5) -> str:
        """Search the web for up-to-date information. Use when you need current docs, error messages, or external references."""
        results = await search_svc.search(query, max_results)
        if not results:
            return "No results found."
        return "\n".join(
            [f"### {r.get('title')}\nURL: {r.get('href')}\n{r.get('body')}\n" for r in results]
        )

    @mcp.tool()
    async def search_stackoverflow(query: str, max_results: int = 3) -> str:
        """
        Search Stack Overflow for technical questions and accepted answers.
        Useful for debugging, finding code examples, and technical solutions.
        """
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
