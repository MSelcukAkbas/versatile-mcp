import json
import os
from datetime import datetime
from typing import Optional
from fastmcp import FastMCP

def register_memory_tools(mcp: FastMCP, memory_svc, task_svc, PROJECT_ROOT, logger):
    @mcp.tool()
    async def memory_store_fact(fact: str, entity: Optional[str] = None, category: Optional[str] = "general", scope: str = "local") -> str:
        """
        Store a personal/project fact in SQLite.
        Scope can be 'local' (project-specific) or 'global' (cross-project).
        """
        return await memory_svc.store_fact(fact, entity, category, scope)

    @mcp.tool()
    async def memory_store_user_habit(habit: str) -> str:
        """
        Store a global user habit, preference, or personality trait.
        These are remembered across ALL projects.
        Example: 'User prefers async/await', 'User likes camelCase'.
        """
        return await memory_svc.store_fact(habit, category="user_habit", scope="global")

    @mcp.tool()
    async def memory_retrieve_facts(query: Optional[str] = None, category: Optional[str] = None, scope: str = "all") -> str:
        """
        Retrieve facts from memory.
        Scope: 'local', 'global', or 'all' (merges both).
        """
        facts = memory_svc.retrieve_facts(query, category, scope)
        return json.dumps(facts, indent=2) if facts else "No facts found."

    @mcp.tool()
    async def memory_index_file(file_path: str) -> str:
        """Index a single file for RAG (stored in local project memory)."""
        try:
            abs_path = file_path if os.path.isabs(file_path) else os.path.join(PROJECT_ROOT, file_path)
            if not os.path.exists(abs_path): return f"Error: {file_path} not found."
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            success = await memory_svc.index_text(content, {"path": file_path}, file_path, scope="local")
            return "SUCCESS" if success else "FAILURE"
        except Exception as e: return str(e)

    @mcp.tool()
    async def memory_index_workspace() -> str:
        """Recursively index all code/text files in the project (local memory)."""
        indexed_count = 0
        allowed_exts = {'.py', '.md', '.txt', '.json', '.yaml', '.js', '.ts', '.html', '.css'}
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if any(file.endswith(ext) for ext in allowed_exts):
                    rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.strip():
                                if await memory_svc.index_text(content, {"path": rel_path}, rel_path, scope="local"):
                                    indexed_count += 1
                    except: continue
        return f"Indexed {indexed_count} files in {PROJECT_ROOT} into local memory."

    @mcp.tool()
    async def memory_search_semantic(query: str, n_results: int = 3, scope: str = "all") -> str:
        """
        Search knowledge base using RAG.
        Scope: 'local', 'global', or 'all' (cross-search).
        """
        results = await memory_svc.search_semantic(query, n_results, scope)
        return json.dumps(results, indent=2) if results else "No matches found."

    @mcp.tool()
    async def task_finalize(summary: str, task_id: Optional[str] = None) -> str:
        """Summarize and finalize the current task for local project memory."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fact = f"[{timestamp}] Task Summary: {summary}"
            await memory_svc.store_fact(fact, category="task_summary", scope="local")
            
            msg = "Task summary archived to local project memory."
            if task_id:
                status_msg = task_svc.mark_step(task_id, 0, "done")
                msg += f" {status_msg}"
            return msg
        except Exception as e:
            return f"Error finalizing task: {str(e)}"

    @mcp.tool()
    async def get_project_history(limit: int = 5) -> str:
        """Retrieve recent task summaries (local) and user preferences (global)."""
        try:
            # 1. Get Local task history
            local_facts = memory_svc.retrieve_facts(category="task_summary", scope="local")
            # 2. Get Global user habits
            global_habits = memory_svc.retrieve_facts(category="user_habit", scope="global")
            
            history = ["--- Recent Project History (Local) ---"]
            for f in local_facts[:limit]:
                history.append(f"{f['timestamp']} - {f['fact']}")
            
            if global_habits:
                history.append("\n--- Your Known Habits & Preferences (Global) ---")
                for h in global_habits[:limit]:
                    history.append(f"- {h['fact']}")
                
            return "\n".join(history)
        except Exception as e:
            return f"Error retrieving history: {str(e)}"
