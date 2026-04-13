# MasterMCP Araç Dokümantasyonu

Bu döküman, sunucuda kayıtlı tüm araçların teknik detaylarını ve LLM'e (asistan) sunulan tam açıklamalarını içerir.

> [!NOTE]
> Bu dosya otomatik olarak oluşturulmuştur. Güncellemek için `scripts/mcp_doc_sync.py` betiğini çalıştırın.

## Araç Listesi

### `apply_patch`
**Açıklama:** 
 Apply a unified diff patch to a file in-place.

---

### `ask_expert`
**Açıklama:** 
 Technical AI expert for code analysis and complex reasoning.

Args:
    prompt: The specific technical question or task description.
    context: Additional textual context (e.g. error logs, snippets).
    file_paths: List of file paths to include (supports 'path/to/file.py:10-50' range).
    background: If True, runs as a background task and returns a task_id.

---

### `check_port`
**Açıklama:** 
 Check whether a TCP port is in use and which process holds it.

---

### `clear_thinking`
**Açıklama:** 
 Clear the current sequential thinking session. Call when starting a new reasoning chain.

---

### `create_directory`
**Açıklama:** 
 Create a new directory.

---

### `create_plan`
**Açıklama:** 
 Analyze a problem and produce a structured execution plan before making changes.

USAGE INSTRUCTIONS FOR THE CALLING MODEL:
- Before calling this tool, reason through the problem thoroughly.
- YOU are responsible for producing the plan content — no external AI is used.
- Populate ALL fields based on your own analysis.

Parameters:
- goal: What the user ultimately wants to achieve.
- context: Relevant technical context (codebase, environment, constraints).
- constraints: Hard limitations or requirements (e.g. "do not modify auth logic").
- problem_analysis: {
    "core_problem": "Short explanation of the real underlying issue",
    "critical_points": ["risk", "edge case", "dependency impact"]
  }
- best_practices: Relevant engineering or architecture guidelines.
- risk_assessment: Possible breaking changes or performance impacts.
- execution_plan: [
    {"step": 1, "action": "...", "expected_result": "..."},
    ...
  ]

Returns: A task_id string you can use with task_mark_step to track progress.

---

### `diff_file_range_with_string`
**Açıklama:** 
 Bir dosyanın belirli bir satır aralığını sağlanan bir metin içeriğiyle karşılaştırır.

Args:
    target_file: Karşılaştırılacak dosyanın yolu.
    text: Dosya içeriğiyle karşılaştırılacak ham metin (string).
    start_line: Dosyanın okunmaya başlanacağı satır (1-indexed, opsiyonel).
    end_line: Dosyanın okunacağı son satır (dahil, opsiyonel).
    context_lines: Diff çıktısında gösterilecek bağlam satır sayısı (varsayılan: 3).

---

### `directory_tree`
**Açıklama:** 
 Returns a flattened 'Indexed File Graph' of the directory, optimized for AI reasoning.
Provides rich metadata (sizes, counts, types, roles) and respects .gitignore rules.

---

### `edit_file`
**Açıklama:** 
 Search and replace content in a file.

---

### `get_file_info`
**Açıklama:** 
 Get detailed metadata for a file.

---

### `get_project_history`
**Açıklama:** 
 Retrieves a consolidated view of recent project activities and established user preferences.

Args:
    project_root (str): Root directory of the project for local history.
    limit (int): Maximum number of recent entries to retrieve. Defaults to 5.
    
Example:
    get_project_history(project_root="C:/MyProject", limit=10)

---

### `get_tool_inventory`
**Açıklama:** 
 Returns all tools with descriptions and current health status.

---

### `http_request`
**Açıklama:** 
 Make an HTTP request to a local or private-network endpoint.
Only localhost and RFC-1918 private IPs are allowed.
method: GET | POST | PUT | DELETE | PATCH

---

### `list_directory`
**Açıklama:** 
 List directory contents.

---

### `list_directory_with_sizes`
**Açıklama:** 
 List directory contents with file sizes.

---

### `manage_background_job`
**Açıklama:** 
 Unified tool for managing background OS processes and internal system tasks.

Actions:
- run: Start a new background terminal command. 'identifier' is the command string.
- status: Check status/output of a job. 'identifier' is the task_id.
- stop: Terminate a job. 'identifier' is the task_id.
- list: List all active background processes and system tasks.
- search: Find system processes by name. 'identifier' is the process name.

---

### `memory_forget`
**Açıklama:** 
 Removes outdated or incorrect memory entries.

Use this when previously stored information becomes invalid
or when indexed content should be removed.

Args:
    type (str): 'fact' or 'file'.
    identifier (str): Fact ID (e.g. 'fact_123') or file path (e.g. 'src/main.py').
    scope (str): 'local' or 'global'.

---

### `memory_index_file`
**Açıklama:** 
 Indexes a single file into the semantic search database.

Use this when a file has been newly created or significantly modified
and should become searchable through semantic queries.

Args:
    file_path (str): Path to the file to be indexed.
    project_root (str, optional): Root directory of the project.

---

### `memory_index_workspace`
**Açıklama:** 
 Indexes the entire workspace for semantic search.

Use this when starting work on a new project or after major architectural changes.
This operation may take time on large repositories.

Args:
    project_root (str, optional): Root directory of the project. Defaults to current workspace.
    background (bool): If True, runs indexing asynchronously in the background.

---

### `memory_retrieve_facts`
**Açıklama:** 
 Retrieves previously stored project facts or user preferences.

Use this when you need to recall configuration decisions,
project details, or stored user preferences.

Args:
    project_root (str): The project path to search in.
    query (str, optional): Keyword or phrase to search for.
    category (str, optional): Filter by fact category.
    scope (str): 'local', 'global', or 'all'. Defaults to 'all'.

---

### `memory_search_semantic`
**Açıklama:** 
 Searches indexed project files using natural language queries.

Uses hybrid search (vector similarity + keyword matching).

Use this when trying to understand how something works in the codebase
or when locating relevant code or documentation.

Args:
    project_root (str): Project root to search in.
    query (str): Natural language question or search phrase.
    n_results (int): Number of results to return. Defaults to 3.
    scope (str): 'local', 'global', or 'all'. Defaults to 'all'.

---

### `memory_store_fact`
**Açıklama:** 
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

---

### `memory_store_user_preference`
**Açıklama:** 
 Stores a recurring user preference or working style globally.

Use this for user habits such as coding style, response format, or communication tone.
Do NOT store project-specific technical facts here.

Args:
    preference (str): The user preference to remember (e.g., 'User prefers concise explanations').

---

### `move_file`
**Açıklama:** 
 Move or rename a file/directory.

---

### `read_env_file`
**Açıklama:** 
 Parse a .env file and return its key-value pairs.
Values whose keys match sensitive patterns (SECRET, TOKEN, PASSWORD, KEY…) are masked.

---

### `read_file`
**Açıklama:** 
 Smart unified file reader for text and rich documents (PDF, DOCX, EPUB).

Args:
    file_path: Path to the target file.
    mode: 'auto' (detect), 'text' (force text), or 'rich' (force doc extraction).
    start_line: Starting line number for text files (1-indexed).
    end_line: Ending line number for text files (inclusive).
    
Note: For PDF/DOCX, line parameters are ignored and 50k char limit applies.
Text files > 5MB require line ranges for safety.

---

### `read_multiple_files`
**Açıklama:** 
 Read multiple files at once.

---

### `remote_ssh_command`
**Açıklama:** 
 Executes a command on a remote server using sshpass through WSL.
This provides a way to connect to remote servers from Windows environments 
where sshpass is otherwise difficult to use.

Args:
    host: Remote server hostname or IP.
    user: SSH username.
    password: SSH password.
    command: The command to execute on the remote server.

---

### `search_files`
**Açıklama:** 
 Search for files matching a pattern.

---

### `search_semantic`
**Açıklama:** 
 ONLY USE THIS TOOL FOR CONCEPTUAL QUERIES. This tool searches the VECTOR DATABASE, not the live file system. If you need to find a specific variable or string in current files, use [grep_search] instead.

This tool uses a semantic retrieval engine to find files and code snippets that match the **meaning** of your query. It is ideal for answering high-level questions about the codebase or locating logic patterns. Returns results in JSON format with code blocks, file paths, and relevance scores.

---

### `search_stackoverflow`
**Açıklama:** 
 Search Stack Overflow for technical questions and accepted answers.

---

### `sequentialthinking`
**Açıklama:** 
 A detailed tool for dynamic reasoning and mini-agent planning.
This tool analyzes your thoughts, fetches auto-memory context, and suggests tools.
adapt and evolve. Each thought can build on, question, or revise previous insights.

When to use this tool:
- Breaking down complex problems into manageable steps.
- Planning and design with room for revision.
- Analysis that might need course correction.
- Problems where the full scope might not be clear initially.

Key features:
- Adjust total_thoughts up or down as you progress.
- Revise previous thoughts using is_revision + revises_thought.
- Branch into alternative approaches using branch_from_thought + branch_id.
- Add more thoughts even after reaching what seemed like the end.

Parameters:
- thought: Your current thinking step (analysis, hypothesis, etc.).
- thought_number: Current number in sequence.
- total_thoughts: Estimated remaining thoughts needed.
- next_thought_needed: True if more thinking is needed.
- context: Optional dict containing current context (e.g. status_code, service names).
- available_tools: Optional list of tool names (strings) you can use.
- memory_keys: Optional list of keywords to auto-retrieve past facts.

---

### `simulate_diagnostic_failure`
**Açıklama:** 
 Simulate a failure for a component (e.g. 'ollama', 'rg') to test Degraded Mode.

---

### `system_info`
**Açıklama:** 
 Return detailed system information about the machine running the MCP server.
Includes OS, platform, CPU, RAM, Python version, and working directory.
Use this to understand the execution environment before running platform-specific commands.

---

### `task_finalize`
**Açıklama:** 
 Records a comprehensive summary of the completed task into the local project memory.

Args:
    summary (str): Detailed text describing what was achieved in the task.
    task_id (str, optional): Identifier of the task being finalized.
    project_root (str, optional): Root directory of the project.
    
Example:
    task_finalize(summary="Implemented JWT authentication and updated the user model schema.")

---

### `task_get_active`
**Açıklama:** 
 Retrieve all active, non-completed plans and their steps.

---

### `task_mark_step`
**Açıklama:** 
 Mark a specific step of a plan as 'todo', 'in_progress', or 'done'.
Call this after completing each step so progress is tracked.

---

### `validate_syntax`
**Açıklama:** 
 Validates code syntax using local high-performance engines (Ruff, Oxlint, Biome).

Supported Extensions:
- Python: .py
- JavaScript: .js, .mjs, .cjs
- TypeScript: .ts, .mts, .cts
- Data/Markup: .json, .yaml, .yml, .xml

Returns 'SUCCESS' if valid, or 'FAILURE: [Error Message]' on syntax error.

---

### `web_search`
**Açıklama:** 
 Search the web for up-to-date information.

---

### `write_env_key`
**Açıklama:** 
 Add or update a key in a .env file.

---

### `write_file`
**Açıklama:** 
 Write or overwrite a file.

---
