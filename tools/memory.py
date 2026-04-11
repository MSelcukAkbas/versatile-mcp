import json
import os
from datetime import datetime
from typing import Optional, Any
from fastmcp import FastMCP
from services.knowledge.memory_service import MemoryService
from services.knowledge.document_service import DocumentService
from services.orchestration.task_service import TaskService

def register_memory_tools(mcp: FastMCP, memory_svc: MemoryService, task_svc: TaskService, doc_svc: DocumentService, PROJECT_ROOT: str, logger: Any, diag_svc: Any):
    @mcp.tool()
    async def memory_store_fact(fact: str, entity: Optional[str] = None, category: Optional[str] = "general", scope: str = "local", project_root: Optional[str] = None) -> str:
        """Store a personal/project fact in SQLite."""
        # Use warning if ollama is down but allow saving to SQL
        err = await diag_svc.check_tool_dependency("memory_store_fact")
        res = await memory_svc.store_fact(fact, entity, category, scope, project_root=project_root)
        return f"{res}\n\nNote: {err}" if err else res

    @mcp.tool()
    async def memory_store_user_habit(habit: str) -> str:
        """Store a global user habit, preference, or personality trait."""
        return await memory_store_fact(habit, category="user_habit", scope="global")

    @mcp.tool()
    async def memory_retrieve_facts(query: Optional[str] = None, category: Optional[str] = None, scope: str = "all", project_root: Optional[str] = None) -> str:
        """Retrieve facts from memory."""
        err = await diag_svc.check_tool_dependency("memory_retrieve_facts")
        if err: return err

        facts = memory_svc.retrieve_facts(query, category, scope, project_root=project_root)
        return json.dumps(facts, indent=2) if facts else "No facts found."

    @mcp.tool()
    async def memory_index_file(file_path: str, project_root: Optional[str] = None) -> str:
        """Index a single file for RAG (local memory)."""
        err = await diag_svc.check_tool_dependency("memory_index_file")
        if err: return err
        try:
            root = project_root or PROJECT_ROOT
            abs_path = file_path if os.path.isabs(file_path) else os.path.join(root, file_path)
            if not os.path.exists(abs_path): return f"Error: {file_path} not found."
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            success = await memory_svc.index_text(content, {"path": file_path}, file_path, scope="local", project_root=project_root)
            return "SUCCESS" if success else "FAILURE"
        except Exception as e: return str(e)

    @mcp.tool()
    async def memory_index_workspace(project_root: Optional[str] = None) -> str:
        """Recursively index all code/text/docs in the project."""
        err = await diag_svc.check_tool_dependency("memory_index_workspace")
        if err: return err

        indexed_count = 0
        root_path = project_root or PROJECT_ROOT
        text_exts = {'.py', '.md', '.txt', '.json', '.yaml', '.js', '.ts', '.html', '.css'}
        doc_exts = {'.pdf', '.docx', '.epub', '.mobi'}
        
        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'models']]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_path)

                if ext in text_exts:
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if content.strip():
                                if await memory_svc.index_text(content, {"path": rel_path}, rel_path, scope="local", project_root=project_root):
                                    indexed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to index text file {rel_path}: {e}")
                
                elif ext in doc_exts:
                    try:
                        text_content = doc_svc.extract_text(full_path)
                        if text_content.strip():
                            # Important: Split large documents into chunks
                            chunks = doc_svc.chunk_text(text_content)
                            for i, chunk in enumerate(chunks):
                                chunk_id = f"{rel_path}#chunk_{i}"
                                metadata = {"path": rel_path, "chunk": i, "total_chunks": len(chunks)}
                                if await memory_svc.index_text(chunk, metadata, chunk_id, scope="local", project_root=project_root):
                                    pass
                            indexed_count += 1
                            logger.info(f"Indexed document {rel_path} in {len(chunks)} chunks.")
                    except Exception as e:
                        logger.error(f"Failed to index document {rel_path}: {e}")

        return f"Indexed {indexed_count} files (including docs) in {root_path} into local memory."

    @mcp.tool()
    async def memory_search_semantic(query: str, n_results: int = 3, scope: str = "all", project_root: Optional[str] = None) -> str:
        """Search knowledge base using RAG."""
        err = await diag_svc.check_tool_dependency("memory_search_semantic")
        if err: return err
        results = await memory_svc.search_semantic(query, n_results, scope, project_root=project_root)
        return json.dumps(results, indent=2) if results else "No matches found."

    @mcp.tool()
    async def task_finalize(summary: str, task_id: Optional[str] = None, project_root: Optional[str] = None) -> str:
        """Summarize and finalize the current task for local project memory."""
        err = await diag_svc.check_tool_dependency("task_finalize")
        if err: return err

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fact = f"[{timestamp}] Task Summary: {summary}"
            res = await memory_store_fact(fact, category="task_summary", scope="local", project_root=project_root)

            msg = f"Task summary processed. {res}"
            if task_id:
                status_msg = task_svc.mark_step(task_id, 0, "done", project_root=project_root)
                msg += f" {status_msg}"
            return msg
        except Exception as e:
            return f"Error finalizing task: {str(e)}"

    @mcp.tool()
    async def get_project_history(limit: int = 5, project_root: Optional[str] = None) -> str:
        """Retrieve recent task summaries (local) and user preferences (global)."""
        err = await diag_svc.check_tool_dependency("get_project_history")
        if err: return err

        try:
            local_facts = memory_svc.retrieve_facts(category="task_summary", scope="local", project_root=project_root)
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
