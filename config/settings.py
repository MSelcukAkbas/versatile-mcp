import os
import pathlib
import hashlib
from typing import Dict, List

# --- Core Paths ---
# SERVER_HOME is the directory where main-source resides
SERVER_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_default_root() -> str:
    """Smart root detection that avoids AppData/Program Files context.
    If run from within the server directory itself, defaults to one level up.
    """
    cwd = os.getcwd()
    
    # If we are running from inside the mcp_master or similar server folder,
    # the project root is likely one level up.
    if cwd.lower() == SERVER_HOME.lower():
        return os.path.dirname(SERVER_HOME)
        
    app_dirs = ["AppData", "Program Files", "System32", "Temp"]
    if any(p.lower() in cwd.lower() for p in app_dirs):
        return os.path.dirname(SERVER_HOME)
        
    return cwd

PROJECT_ROOT = os.getenv("PROJECT_ROOT", get_default_root())

# --- Centralized Storage Config ---
GLOBAL_DATA_DIR = os.getenv("MCP_MASTER_DATA_DIR", os.path.join(os.path.expanduser("~"), ".mcp-master"))

def get_project_id(path: str) -> str:
    """Generate a slug-based unique ID for the current project.
    Uses pathlib for cross-platform and case-sensitivity normalization.
    """
    try:
        abs_path = str(pathlib.Path(path).resolve())
    except:
        abs_path = os.path.abspath(path)
        
    folder_name = os.path.basename(abs_path) or "root"
    path_hash = hashlib.md5(abs_path.lower().encode()).hexdigest()[:8]
    return f"{folder_name}-{path_hash}"

PROJECT_ID = get_project_id(PROJECT_ROOT)
LOCAL_DATA_DIR = os.path.join(GLOBAL_DATA_DIR, "projects", PROJECT_ID)

# --- Access Control ---
ALLOWED_ROOTS: List[str] = [
    str(pathlib.Path(PROJECT_ROOT).resolve()),
    str(pathlib.Path(SERVER_HOME).resolve()),
    str(pathlib.Path.home().resolve()),
]

# Additional roots can be added via environment variable
extra_roots = os.getenv("ADDITIONAL_ROOTS", "")
if extra_roots:
    ALLOWED_ROOTS.extend([str(pathlib.Path(p.strip()).resolve()) for p in extra_roots.split(",")])

# --- Data & Service Paths ---
def build_paths(project_root: str, project_id: str) -> Dict[str, str]:
    """Build PATHS dict for a given project."""
    local_data_dir = os.path.join(GLOBAL_DATA_DIR, "projects", project_id)
    return {
        "SERVER_HOME": SERVER_HOME,
        "PROJECT_ROOT": project_root,
        "GLOBAL_DATA": GLOBAL_DATA_DIR,
        "LOCAL_DATA": local_data_dir,
        "prompts": os.path.join(SERVER_HOME, "prompts"),
        "local_memory": os.path.join(local_data_dir, "memory"),
        "global_memory": os.path.join(GLOBAL_DATA_DIR, "global", "memory"),
        "memory": os.path.join(local_data_dir, "memory"),
        "tasks": os.path.join(local_data_dir, "tasks.json"),
        "audit_logs": os.path.join(GLOBAL_DATA_DIR, "global", "audit_logs"),  # Global, not per-project
        "requirements": os.path.join(SERVER_HOME, "requirements.txt"),
        "default_ignores": os.path.join(SERVER_HOME, "config", "default_ignores.txt"),
        "models": os.path.join(SERVER_HOME, "models"),
        "embedding_model": os.path.join(SERVER_HOME, "models", "paraphrase-multilingual-MiniLM-L12-118M-v2-Q8_0.gguf"),
    }

PATHS: Dict[str, str] = build_paths(PROJECT_ROOT, PROJECT_ID)

def resolve_paths(project_root: str) -> Dict[str, str]:
    """
    Get paths for a specific project_root.
    This is the core for dynamic, multi-project support.
    """
    if not project_root:
        raise ValueError("project_root is mandatory for dynamic path resolution.")
        
    project_id = get_project_id(project_root)
    return build_paths(project_root, project_id)

# --- Service Settings ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-coder:7b-instruct-q4_K_M")
MAX_INDEX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
STACK_EXCHANGE_API_KEY = os.getenv("STACK_EXCHANGE_API_KEY")

# --- Directory Initialization ---
def ensure_directories(paths: Dict[str, str] | None = None):
    """Ensure that all necessary data directories exist."""
    if paths is None:
        paths = PATHS
    required_dirs = [
        paths["local_memory"],
        paths["global_memory"],
        paths["audit_logs"]
    ]
    for d in required_dirs:
        os.makedirs(d, exist_ok=True)
