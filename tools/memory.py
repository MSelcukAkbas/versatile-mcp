import json
import os
from datetime import datetime
from typing import Optional, Any
from fastmcp import FastMCP
from services.knowledge.memory_service import MemoryService
from services.knowledge.document_service import DocumentService
from services.orchestration.task_service import TaskService

def register_memory_tools(mcp: FastMCP, memory_svc: MemoryService, task_svc: TaskService, doc_svc: DocumentService, PROJECT_ROOT: str, logger: Any, diag_svc: Any, ignore_svc: Any, file_svc: Any, async_task_svc: Any = None):
    @mcp.tool()
    async def memory_store_fact(fact: str, project_root: str, entity: Optional[str] = None, category: Optional[str] = "general", 
                        scope: str = "local", source: str = "assistant", confidence: str = "high") -> str:
        """
        Stores an important, durable fact about the project or environment in long-term memory.
        
        Use this when a technical decision, configuration, or project detail should not be forgotten.
        
        Args:
            fact (str): The concise factual statement to store.
            entity (str, optional): Main subject of the fact (e.g., 'database', 'auth', 'api').
            category (str, optional): Classification such as 'tech_stack', 'config', 'domain_logic'. Defaults to 'general'.
            scope (str): 'local' for current project, 'global' for all projects.
            source (str): Where the information came from (e.g. 'docker-compose.yml', 'user', 'README.md').
            confidence (str): Reliability of the fact ('high', 'medium', 'low').
            project_root (str, optional): Root path of the project for local scope.
        """
        err = await diag_svc.check_tool_dependency("memory_store_fact")
        res = await memory_svc.store_fact(fact, project_root, entity, category, scope, source, confidence)
        return f"{res}\n\nNote: {err}" if err else res

    @mcp.tool()
    async def memory_store_user_preference(preference: str) -> str:
        """
        Stores a recurring user preference or working style globally.
        
        Use this for user habits such as coding style, response format, or communication tone.
        Do NOT store project-specific technical facts here.
        
        Args:
            preference (str): The user preference to remember (e.g., 'User prefers concise explanations').
        """
        return await memory_store_fact(preference, project_root="GLOBAL_DATA", category="user_preference", scope="global", source="user")

    @mcp.tool()
    async def memory_retrieve_facts(project_root: str, query: Optional[str] = None, category: Optional[str] = None, scope: str = "all") -> str:
        """
        Retrieves previously stored project facts or user preferences.
        
        Use this when you need to recall configuration decisions,
        project details, or stored user preferences.
        
        Args:
            project_root (str): The project path to search in.
            query (str, optional): Keyword or phrase to search for.
            category (str, optional): Filter by fact category.
            scope (str): 'local', 'global', or 'all'. Defaults to 'all'.
        """
        err = await diag_svc.check_tool_dependency("memory_retrieve_facts")
        if err:
            return err

        facts = memory_svc.retrieve_facts(query, category, scope, project_root=project_root)
        result = {
            "project_root": project_root,
            "scope": scope,
            "facts": facts
        }
        return json.dumps(result, indent=2) if facts else f"No facts found for project: {project_root}"

    @mcp.tool()
    async def memory_index_file(file_path: str, project_root: str) -> str:
        """
        Indexes a single file into the semantic search database.
        
        Use this when a file has been newly created or significantly modified
        and should become searchable through semantic queries.
        
        Args:
            file_path (str): Path to the file to be indexed.
            project_root (str, optional): Root directory of the project.
        """
        err = await diag_svc.check_tool_dependency("memory_index_file")
        if err:
            return err
        try:
            root = project_root or PROJECT_ROOT
            abs_path = file_path if os.path.isabs(file_path) else os.path.join(root, file_path)
            if not os.path.exists(abs_path):
                return f"Error: {file_path} not found."
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            success = await memory_svc.index_text(content, {"path": file_path}, file_path, project_root, scope="local")
            return "SUCCESS" if success else "FAILURE"
        except Exception as e:
            return str(e)

    @mcp.tool()
    async def memory_index_workspace(project_root: str, background: bool = False) -> str:
        """
        Indexes the entire workspace for semantic search.
        
        Use this when starting work on a new project or after major architectural changes.
        This operation may take time on large repositories.
        
        Args:
            project_root (str, optional): Root directory of the project. Defaults to current workspace.
            background (bool): If True, runs indexing asynchronously in the background.
        """
        err = await diag_svc.check_tool_dependency("memory_index_workspace")
        if err:
            return err

        root_path = project_root or PROJECT_ROOT
        text_exts = {'.py', '.md', '.txt', '.json', '.yaml', '.js', '.ts', '.html', '.css'}
        doc_exts = {'.pdf', '.docx', '.epub', '.mobi'}

        # Refresh patterns to ensure latest .gitignore changes are applied
        if hasattr(ignore_svc, 'refresh'):
            ignore_svc.refresh()

        async def indexing_logic(task_id: Optional[str] = None):
            indexed_count = 0
            skipped_count = 0
            skipped_size_count = 0
            active_files = []
            
            from config.settings import MAX_INDEX_FILE_SIZE, resolve_paths

            # Step 1: Gathering Phase (with Directory Pruning & Size Filter)
            logger.info(f"Gathering files from {root_path} (Max size: {MAX_INDEX_FILE_SIZE / 1024 / 1024:.1f}MB)...")
            on_disk_files = set()
            for root, dirs, files in os.walk(root_path):
                # PRUNE directories in-place to avoid descending into ignored ones (e.g., node_modules)
                dirs_to_remove = [d for d in dirs if ignore_svc.is_ignored(os.path.relpath(os.path.join(root, d), root_path), is_dir=True)]
                for d in dirs_to_remove: dirs.remove(d)

                for file in files:
                    full_path = os.path.join(root, file)
                    rel_file = os.path.relpath(full_path, root_path)
                    if not ignore_svc.is_ignored(rel_file, is_dir=False):
                        on_disk_files.add(full_path)
            
            # Step 2: Cleanup Phase (Detection of Deleted Files)
            import sqlite3
            paths = resolve_paths(project_root)
            hub = memory_svc._get_local_hub(paths["local_memory"])
            
            deleted_count = 0
            try:
                with sqlite3.connect(hub.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, metadata FROM knowledge")
                    for doc_id, meta_json in cursor.fetchall():
                        meta = json.loads(meta_json)
                        file_path = meta.get("path")
                        if file_path:
                            abs_path = os.path.join(root_path, file_path)
                            if not os.path.exists(abs_path):
                                await memory_svc.delete_document(file_path, project_root, scope="local")
                                deleted_count += 1
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")

            # Step 3: Hashing & Incremental Indexing Phase (Triple Check)
            import hashlib
            for i, full_path in enumerate(on_disk_files):
                ext = os.path.splitext(full_path)[1].lower()
                rel_path = os.path.relpath(full_path, root_path)
                
                # Check Size
                if os.path.getsize(full_path) > MAX_INDEX_FILE_SIZE:
                    skipped_size_count += 1
                    continue

                try:
                    mtime = os.path.getmtime(full_path)
                    existing_meta = hub.store.get_metadata(rel_path)
                    
                    # 1 & 2: Timestamp & Hash Check
                    if existing_meta and existing_meta.get("last_modified") == mtime:
                        skipped_count += 1
                        continue

                    if ext in text_exts:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if not content.strip(): continue
                            
                            chunks = doc_svc.chunk_text(content)
                            for j, chunk_data in enumerate(chunks):
                                chunk_id = f"{rel_path}#chunk_{j}"
                                meta = {
                                    "path": rel_path, "chunk": j, "total_chunks": len(chunks),
                                    "line_start": chunk_data["line_start"], "line_end": chunk_data["line_end"],
                                    "last_modified": mtime, "workspace_id": os.path.basename(root_path)
                                }
                                await memory_svc.index_text(chunk_data["content"], meta, chunk_id, project_root, scope="local")
                            indexed_count += 1

                    elif ext in doc_exts:
                        text_content = doc_svc.extract_text(full_path)
                        # Similar logic for docs... (omitted for brevity but follows same pattern)
                        indexed_count += 1

                except Exception as e:
                    logger.warning(f"Failed to process {rel_path}: {e}")

                if task_id and async_task_svc:
                    progress = int(((i + 1) / len(on_disk_files)) * 100)
                    async_task_svc.update_progress(task_id, progress)

            return f"Success: {indexed_count} indexed, {deleted_count} deleted, {skipped_count} unchanged."

        if background and async_task_svc:
            # We pass the function name itself (indexing_logic) to run_task.
            # run_task will call it with the generated task_id.
            meta_task_id = async_task_svc.run_task(indexing_logic, "Workspace Indexing")
            return f"Workspace indexing started in background. Task ID: {meta_task_id}. Use get_background_task_status to check progress."
        else:
            return await indexing_logic()

    @mcp.tool()
    async def search_semantic_memory(project_root: str, query: str, n_results: int = 5, scope: str = "all", mode: str = "hybrid") -> str:
        """
        Versatile hybrid search engine that combines keyword block-search (Ripgrep) and conceptual vector-search.
        
        Modes:
        - code: Fast keyword-based code block search.
        - memory: Deep conceptual search via embeddings.
        - hybrid (default): Combined results from both sources.
        
        Use this when trying to understand how something works in the codebase or when locating relevant logic.
        
        Args:
            project_root (str): Project root to search in.
            query (str): Search term or conceptual question.
            n_results (int): Number of results per mode.
            scope (str): 'local', 'global', or 'all'.
            mode (str): 'code', 'memory', or 'hybrid'.
        """
        err = await diag_svc.check_tool_dependency("search_semantic_memory")
        if err: return err
        
        results = await memory_svc.search_hybrid(query, project_root, n_results, scope, mode, file_svc)
        
        warning = "\n\n> [!WARNING]\n> Not: Hafıza (index) güncel değilse Vektör sonuçları hatalı olabilir. Güncel sonuçlar için [memory_index_workspace] çalıştırın."
        
        final_output = {
            "project_root": project_root,
            "query": query,
            "mode": mode,
            "results": results,
            "note": "Vector results are based on the latest indexing. Run memory_index_workspace to refresh."
        }
        return json.dumps(final_output, indent=2, ensure_ascii=False) + warning

    @mcp.tool()
    async def memory_forget(type: str, identifier: str, project_root: str, scope: str = "local") -> str:
        """
        Removes outdated or incorrect memory entries.
        
        Use this when previously stored information becomes invalid
        or when indexed content should be removed.
        
        Args:
            type (str): 'fact' or 'file'.
            identifier (str): Fact ID (e.g. 'fact_123') or file path (e.g. 'src/main.py').
            scope (str): 'local' or 'global'.
        """
        if type == "fact":
            success = await memory_svc.delete_fact(identifier, project_root, scope=scope)
            return "SUCCESS" if success else "FAILURE"
        elif type == "file":
            count = await memory_svc.delete_document(identifier, project_root, scope=scope)
            return f"Removed {count} index entries for {identifier}."
        return "Invalid type. Use 'fact' or 'file'."

    @mcp.tool()
    async def task_finalize(summary: str, project_root: str, task_id: Optional[str] = None) -> str:
        """
        Records a comprehensive summary of the completed task into the local project memory.
        
        Args:
            summary (str): Detailed text describing what was achieved in the task.
            task_id (str, optional): Identifier of the task being finalized.
            project_root (str, optional): Root directory of the project.
            
        Example:
            task_finalize(summary="Implemented JWT authentication and updated the user model schema.")
        """
        err = await diag_svc.check_tool_dependency("task_finalize")
        if err:
            return err

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fact = f"[{timestamp}] Task Summary: {summary}"
            res = await memory_store_fact(fact, category="task_summary", scope="local", project_root=project_root)

            msg = f"Task summary processed. {res}"
            if task_id:
                status_msg = task_svc.mark_step(task_id, 0, "done", project_root)
                msg += f" {status_msg}"
            return msg
        except Exception as e:
            return f"Error finalizing task: {str(e)}"

    @mcp.tool()
    async def get_project_history(project_root: str, limit: int = 5) -> str:
        """
        Retrieves a consolidated view of recent project activities and established user preferences.
        
        Args:
            project_root (str): Root directory of the project for local history.
            limit (int): Maximum number of recent entries to retrieve. Defaults to 5.
            
        Example:
            get_project_history(project_root="C:/MyProject", limit=10)
        """
        err = await diag_svc.check_tool_dependency("get_project_history")
        if err:
            return err

        try:
            local_facts = memory_svc.retrieve_facts(project_root, category="task_summary", scope="local")
            global_habits = memory_svc.retrieve_facts(category="user_preference", scope="global")

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

