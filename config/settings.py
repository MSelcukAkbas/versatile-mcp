import os
import pathlib
import hashlib
from typing import Dict, List

# --- Core Paths ---
# SERVER_HOME is the directory where main-source resides
SERVER_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_default_root() -> str:
    """Smart root detection that avoids AppData/Program Files context if run from CLI."""
    cwd = os.getcwd()
    app_dirs = ["AppData", "Program Files", "System32", "Temp"]
    if any(p.lower() in cwd.lower() for p in app_dirs):
        return os.path.dirname(SERVER_HOME)
    return cwd

PROJECT_ROOT = os.getenv("PROJECT_ROOT", get_default_root())

# --- Centralized Storage Config ---
GLOBAL_DATA_DIR = os.getenv("MCP_MASTER_DATA_DIR", os.path.join(os.path.expanduser("~"), ".mcp-master"))

def get_project_id(path: str) -> str:
    """Generate a slug-based unique ID for the current project."""
    abs_path = os.path.abspath(path)
    folder_name = os.path.basename(abs_path) or "root"
    path_hash = hashlib.md5(abs_path.encode()).hexdigest()[:8]
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
PATHS: Dict[str, str] = {
    "SERVER_HOME": SERVER_HOME,
    "PROJECT_ROOT": PROJECT_ROOT,
    "GLOBAL_DATA": GLOBAL_DATA_DIR,
    "LOCAL_DATA": LOCAL_DATA_DIR,
    "prompts": os.path.join(SERVER_HOME, "prompts"),
    "local_memory": os.path.join(LOCAL_DATA_DIR, "memory"),
    "global_memory": os.path.join(GLOBAL_DATA_DIR, "global", "memory"),
    "memory": os.path.join(LOCAL_DATA_DIR, "memory"), # Backward compatibility alias
    "tasks": os.path.join(LOCAL_DATA_DIR, "tasks.json"),
    "audit_logs": os.path.join(LOCAL_DATA_DIR, "audit_logs"),
    "requirements": os.path.join(SERVER_HOME, "requirements.txt"),
}

# --- Service Settings ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-coder:7b-instruct-q4_K_M")
STACK_EXCHANGE_API_KEY = os.getenv("STACK_EXCHANGE_API_KEY")

# --- Directory Initialization ---
def ensure_directories():
    """Ensure that all necessary data directories exist."""
    required_dirs = [
        PATHS["local_memory"],
        PATHS["global_memory"],
        PATHS["audit_logs"]
    ]
    for d in required_dirs:
        os.makedirs(d, exist_ok=True)
