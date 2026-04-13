import os
import sys
from pathlib import Path

# Ensure the project root is in sys.path for internal imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP

# 1. Configuration & Paths
from config.settings import PATHS, ALLOWED_ROOTS, OLLAMA_HOST, ensure_directories

# Windows UTF-8 Enforcement
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 2. Service Imports
# Core
from services.core.bin_service import BinService
from services.core.diagnostic_service import DiagnosticService
from services.core.file_service import FileService
from services.core.validation_service import ValidationService
from services.core.logger_service import setup_logger, log_startup_banner
from services.core.process_service import ProcessService
from services.core.ignore_service import IgnoreService
from services.core.async_task_service import AsyncTaskService
from services.core.workspace_analyzer import WorkspaceAnalyzer
from services.knowledge.http_client_service import HttpClientService

# AI
from services.ai.ollama_service import OllamaService
from services.ai.prompt_service import PromptService
from services.ai.thinking_service import ThinkingService
from services.ai.llama_service import LlamaService

# Knowledge
from services.knowledge.document_service import DocumentService
from services.knowledge.search_service import SearchService
from services.knowledge.stackoverflow_service import StackOverflowService
from services.knowledge.memory_service import MemoryService

# Orchestration
from services.orchestration.planner_service import PlannerService
from services.orchestration.task_service import TaskService

# 3. Tool Registration
from tools import register_all_tools

def bootstrap():
    """Build and return the configured FastMCP server."""
    
    # Initialize logger FIRST so everything below is captured
    logger = setup_logger("MasterMCP")
    log_startup_banner(logger)

    # 0. Environment Verification & Auto-Setup
    logger.info("Bootstrap | Checking dependencies...")
    
    ensure_directories()
    
    mcp = FastMCP("Versatile-MCP")
    
    logger.info("Bootstrap | Initializing services...")
    
    logger.debug("Initializing BinService...")
    bin_svc = BinService(PATHS["PROJECT_ROOT"])
    
    logger.debug("Initializing OllamaService...")
    ollama_svc = OllamaService(host=OLLAMA_HOST)
    
    logger.debug("Initializing LlamaService (Lazy)...")
    llama_svc = LlamaService() # model_path=None trigger lazy loading later
    
    logger.debug("Initializing DocumentService...")
    doc_svc = DocumentService()
    
    logger.debug("Initializing IgnoreService...")
    ignore_svc = IgnoreService(PATHS["default_ignores"], PATHS["PROJECT_ROOT"])
    
    logger.debug("Initializing MemoryService...")
    memory_svc = MemoryService(PATHS["local_memory"], PATHS["global_memory"], llama_svc)
    
    logger.debug("Initializing FileService...")
    file_svc = FileService(ALLOWED_ROOTS, ignore_svc)
    
    logger.debug("Initializing ThinkingService (Autonomous & In-Memory Loop Detection)...")
    thinking_svc = ThinkingService(memory_svc=memory_svc, file_svc=file_svc)
    
    logger.info("Bootstrap | Core services initialized. Assembling mapping...")
    
    services = {
        "file": file_svc,
        "ollama": ollama_svc,
        "llama": llama_svc,
        "doc": doc_svc,
        "bin": bin_svc,
        "diag": DiagnosticService(ollama_svc, bin_svc),
        "prompt": PromptService(PATHS["prompts"]),
        "search": SearchService(),
        "stackoverflow": StackOverflowService(api_key=os.getenv("STACK_EXCHANGE_API_KEY")),
        "planner": PlannerService(),
        "validator": ValidationService(),
        "thinking": thinking_svc,
        "memory": memory_svc,
        "task": TaskService(PATHS["tasks"]),
        "logger": logger,
        "process": ProcessService(Path(PATHS["SERVER_HOME"]) / ".mcp-master"),
        "http": HttpClientService(),
        "ignore": ignore_svc,
        "async_task": AsyncTaskService(),
        "workspace": WorkspaceAnalyzer(PATHS["PROJECT_ROOT"], ignore_svc=ignore_svc),
    }
    logger.info(f"Bootstrap | {len(services)} services ready.")
    
    # Register All Tools
    register_all_tools(mcp, services, PATHS)
    logger.info("Bootstrap | All tools registered. Server ready.")
    
    return mcp, logger

if __name__ == "__main__":
    mcp_app, app_logger = bootstrap()
    
    # Allow override via environment variables (for Docker/Network use)
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))

    app_logger.info(f"Master MCP Server starting (transport={transport}, host={host}, port={port})...")
    
    try:
        if transport == "stdio":
            mcp_app.run()
        else:
            # For SSE or HTTP
            app_logger.info(f"SSE Dashboard available at http://{host}:{port}")
            mcp_app.run(transport=transport, host=host, port=port)
    except Exception as e:
        app_logger.critical(f"FATAL ERROR: Server failed to start or crashed: {e}", exc_info=True)
        sys.exit(1)
