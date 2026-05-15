import json
from fastmcp import FastMCP

def register_memory_tools(mcp: FastMCP, memory_svc, analyzer_svc, ignore_svc, validate_project_root):
    
    @mcp.tool()
    async def commit_knowledge(fact: str, project_root: str, category: str = "general") -> str:
        """
        Permanently stores a critical fact, rule, or architectural decision in the project's permanent memory.
        Use this to remember cross-session insights, custom rules, or specific codebase patterns that LLMs might forget.
        
        IMPORTANT: 'project_root' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') to ensure data is stored in the correct project container.
        
        Args:
            fact: Specific technical information, rule, or decision to remember (concise but clear).
            project_root: The ABSOLUTE path to the project root. DO NOT use relative paths.
            category: A classification tag (e.g., "architecture", "security", "deployment_rules", "coding_standard").
        """
        project_root = validate_project_root(project_root)
        result = await memory_svc.commit_knowledge(fact, project_root, category=category)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def search_knowledge(query: str, project_root: str, n: int = 5, min_score: float = 0.4) -> str:
        """
        Performs a high-performance semantic search across manually stored knowledge (facts).
        This tool uses vector embeddings to find relevant architectural decisions or rules even if the keywords don't match exactly.
        
        IMPORTANT: 'project_root' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') to locate the correct vector store.
        
        Args:
            query: Natural language question or search term.
            project_root: The ABSOLUTE path to the project root. DO NOT use relative paths.
            n: Maximum number of relevant results to return.
            min_score: Similarity threshold (0.0 to 1.0). 0.4+ is recommended for high precision.
        """
        project_root = validate_project_root(project_root)
        results = await memory_svc.search(query, project_root, n=n, min_score=min_score)
        return json.dumps({"results": results}, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def list_knowledge(project_root: str, query: str = None, category: str = None) -> str:
        """
        Retrieves a structured list of all stored knowledge, facts, and rules for the specified project.
        Supports filtering by keyword (query) or category to audit the project's memory.
        
        IMPORTANT: 'project_root' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') to access the correct memory database.
        
        Args:
            project_root: The ABSOLUTE path to the project root. DO NOT use relative paths.
            query: Optional keyword to filter facts by content.
            category: Optional tag to filter facts by their assigned category.
        """
        project_root = validate_project_root(project_root)
        facts = memory_svc.list_knowledge(project_root, query=query, category=category)
        return json.dumps(facts, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def manage_knowledge(action: str, fact_id: int, project_root: str, new_fact: str = None) -> str:
        """
        Updates or deletes existing records in the project's permanent memory.
        Use this to refine old rules, correct outdated decisions, or clean up the memory state.
        
        IMPORTANT: 'project_root' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') to target the correct database.
        
        Args:
            action: Either "update" (to modify text) or "delete" (to permanently remove).
            fact_id: The unique integer ID of the knowledge record (get this from list_knowledge).
            project_root: The ABSOLUTE path to the project root. DO NOT use relative paths.
            new_fact: The updated content (REQUIRED if action is "update").
        """
        project_root = validate_project_root(project_root)
        if action == "delete":
            result = await memory_svc.delete_knowledge(fact_id, project_root)
        elif action == "update":
            if not new_fact:
                return json.dumps({"status": "error", "message": "new_fact required for update"}, ensure_ascii=False)
            result = await memory_svc.update_knowledge(fact_id, new_fact, project_root)
        else:
            return json.dumps({"status": "error", "message": f"Invalid action: {action}"}, ensure_ascii=False)
            
        return json.dumps(result, indent=2, ensure_ascii=False)
