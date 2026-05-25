import sys
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from fastmcp import FastMCP

# 1. Path Setup (Ensure core and servers are importable)
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)


# Add master path specifically for its internal logic
master_path = os.path.join(root_path, "servers", "master")
if master_path not in sys.path:
    sys.path.insert(0, master_path)

# Redirect default stdout to stderr for protocol safety
_real_stdout = sys.stdout
sys.stdout = sys.stderr

# 4. Initialization (MUST BE BEFORE IMPORTS)
load_dotenv(os.path.join(root_path, ".env"))

# 2. Core Imports
from core.config import Config, validate_project_root
from core.helpers.ignores import IgnoreService
from core.helpers.embedder import Embedder
from core.helpers.chunker import Chunker

# 3. Server-Specific Imports
# Brain - Storage
from servers.brain.storage.hybrid_store import HybridStore

# Brain - Services
from servers.brain.services.memory_service import MemoryService
from servers.brain.services.graph_service import GraphService
from servers.brain.services.reasoning_service import ReasoningService
from servers.brain.services.distillation_service import DistillationService
from servers.brain.services.retrieval_pipeline import RetrievalPipeline
from servers.brain.services.analysis.service import WorkspaceAnalyzerService

# Brain - Tools
from servers.brain.tools.memory_tools import register_memory_tools
from servers.brain.tools.reasoning_tools import register_reasoning_tools
from servers.brain.tools.graph_tools import register_graph_tools
from servers.brain.tools.codebase_tools import register_codebase_tools
from servers.brain.tools.user_tools import register_user_tools
from servers.brain.tools.project_tools import register_project_tools
from servers.brain.tools.workspace import register_workspace_tools

# Master
from resources.config.settings import PATHS, ALLOWED_ROOTS, ensure_directories
from servers.master.services.core.logger_service import setup_logger
from servers.master.services.filesystem import FileSystemService
from servers.master.services.system.bin_service import BinService
from servers.master.services.system.diagnostic_service import DiagnosticService
from servers.master.services.system.validation_service import ValidationService
from servers.master.services.system.document_service import DocumentService
from servers.master.tools import register_all_tools

# Remote
from servers.remote.main import register_remote_tools

# 5. Global Logging Setup
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
    force=True
)
logger = logging.getLogger("Versatile-Mcp-Unified")
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

Config.setup()
ensure_directories()

logger.info(f"Initialized with DATA_DIR: {Config.DATA_DIR}")
logger.info(f"Initialized with MODEL_PATH: {Config.MODEL_PATH}")

# 6. FastMCP App Instance
mcp = FastMCP("Versatile-Mcp")

# 7. Initialize & Register ALL Services
# --- Shared Helpers ---
ignore_svc = IgnoreService(project_root=".", default_ignore_path=PATHS["default_ignores"])

# --- Brain Cluster (Versatile-Memory Integration) ---
embedder = Embedder(
    Config.MODEL_PATH,
    n_gpu_layers=Config.N_GPU_LAYERS,
    n_threads=Config.N_THREADS,
    n_ctx=Config.N_CTX,
)
chunker = Chunker(chunk_size=Config.CHUNK_SIZE, chunk_overlap=Config.CHUNK_OVERLAP)

hybrid_store = HybridStore(
    data_dir=Config.DATA_DIR,
    embedder=embedder,
    timeout=Config.DB_TIMEOUT,
)

memory_svc = MemoryService(hybrid_store)
graph_svc = GraphService(hybrid_store.sqlite)
reasoning_svc = ReasoningService(hybrid_store, embedder, memory_svc=memory_svc)
distillation_svc = DistillationService(hybrid_store, memory_svc)
retrieval_pipeline = RetrievalPipeline(hybrid_store, embedder, graph_svc)

analyzer_svc = WorkspaceAnalyzerService(ignore_svc)

# Register Brain Tools
register_memory_tools(mcp, memory_svc, retrieval_pipeline=retrieval_pipeline)
register_reasoning_tools(mcp, reasoning_svc, distillation_svc)
register_graph_tools(mcp, graph_svc)
register_codebase_tools(mcp)
register_user_tools(mcp, memory_svc, retrieval_pipeline)
register_project_tools(mcp, memory_svc, retrieval_pipeline)
register_workspace_tools(mcp, memory_svc, ignore_svc, analyzer_svc, validate_project_root)

# --- Master Cluster ---
bin_svc = BinService(PATHS["PROJECT_ROOT"])
validation_svc = ValidationService()
file_svc = FileSystemService(ALLOWED_ROOTS, ignore_svc, bin_svc)
doc_svc = DocumentService()
diag_svc = DiagnosticService(bin_svc)

master_services = {
    "file": file_svc, "bin": bin_svc, "ignore": ignore_svc,
    "diag": diag_svc, "validator": validation_svc,
    "doc": doc_svc, "logger": logger
}
register_all_tools(mcp, master_services, PATHS)

# --- Remote Cluster ---
register_remote_tools(mcp, root_path)

logger.info("Versatile-Mcp | Unified Suite | 30+ Tools Loaded | Ready.")

if __name__ == "__main__":
    sys.stdout = _real_stdout
    mcp.run(show_banner=False)
