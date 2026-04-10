import os
import sys
from fastmcp import FastMCP

# 1. Configuration & Paths
from config.settings import PATHS, ALLOWED_ROOTS, OLLAMA_HOST, ensure_directories

# Windows UTF-8 Enforcement
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 2. Service Imports
from services.env_service import EnvService
from services.bin_service import BinService
from services.ollama_service import OllamaService
from services.diagnostic_service import DiagnosticService
from services.file_service import FileService
from services.prompt_service import PromptService
from services.search_service import SearchService
from services.stackoverflow_service import StackOverflowService
from services.planner_service import PlannerService
from services.validation_service import ValidationService
from services.thinking_service import ThinkingService
from services.memory_service import MemoryService
from services.task_service import TaskService
from services.audit_service import AuditService, AuditMiddleware
from services.logger_service import setup_logger, log_startup_banner

# 3. Tool Registration
from tools import register_all_tools

def bootstrap():
    """Build and return the configured FastMCP server."""
    
    # Initialize logger FIRST so everything below is captured
    logger = setup_logger("MasterMCP")
    log_startup_banner(logger)

    # 0. Environment Verification & Auto-Setup
    logger.info("Bootstrap | Checking dependencies...")
    EnvService.check_and_install_dependencies(PATHS["requirements"])
    
    ensure_directories()
    
    mcp = FastMCP("Versatile-MCP")
    
    logger.info("Bootstrap | Initializing services...")
    bin_svc = BinService(PATHS["PROJECT_ROOT"])
    ollama_svc = OllamaService(host=OLLAMA_HOST)
    
    services = {
        "file": FileService(ALLOWED_ROOTS),
        "ollama": ollama_svc,
        "bin": bin_svc,
        "diag": DiagnosticService(ollama_svc, bin_svc),
        "prompt": PromptService(PATHS["prompts"]),
        "search": SearchService(),
        "stackoverflow": StackOverflowService(api_key=os.getenv("STACK_EXCHANGE_API_KEY")),
        "planner": PlannerService(),
        "validator": ValidationService(),
        "thinking": ThinkingService(),
        "memory": MemoryService(PATHS["local_memory"], PATHS["global_memory"]),
        "task": TaskService(PATHS["tasks"]),
        "audit": AuditService(PATHS["audit_logs"]),
        "logger": logger
    }
    logger.info(f"Bootstrap | {len(services)} services initialized.")
    
    # Register Middleware
    mcp.add_middleware(AuditMiddleware(services["audit"]))
    logger.info("Bootstrap | AuditMiddleware registered (JSONL format).")
    
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
    
    if transport == "stdio":
        mcp_app.run()
    else:
        # For SSE or HTTP
        mcp_app.run(transport=transport, host=host, port=port)
