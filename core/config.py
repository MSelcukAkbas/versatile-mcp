import os
import logging
from pathlib import Path
from typing import Optional

class Config:
    """Unified configuration for all Versatile-Mcp servers, including advanced RAG and Reasoning."""
    
    # Base Paths (Calculated at class level)
    CORE_DIR = Path(__file__).parent.parent.resolve()
    DEFAULT_DATA_DIR = os.path.expanduser("~/.versatile-mcp")
    
    # Global
    _data_raw = os.getenv("MCP_DATA_DIR", DEFAULT_DATA_DIR)
    DATA_DIR = os.path.abspath(os.path.join(str(CORE_DIR), _data_raw)) if not os.path.isabs(_data_raw) else _data_raw
    
    DB_TIMEOUT = int(os.getenv("MCP_DB_TIMEOUT", "30"))
    
    # Brain (Memory & Embedding)
    _model_raw = os.getenv("EMBEDDING_MODEL_PATH")
    # Resolve relative paths against the project root
    if _model_raw and not os.path.isabs(_model_raw):
        MODEL_PATH = os.path.abspath(os.path.join(str(CORE_DIR), _model_raw))
    else:
        MODEL_PATH = _model_raw

    # RAG Chunking & Retrieval Parameters
    CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "512"))
    CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "64"))
    TOP_K = int(os.getenv("RAG_TOP_K", "5"))
    MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.0"))
    
    # Llama Engine Embedding Params
    N_GPU_LAYERS = int(os.getenv("RAG_N_GPU_LAYERS", "0"))
    N_THREADS = int(os.getenv("RAG_N_THREADS", "4"))
    N_CTX = int(os.getenv("RAG_N_CTX", "2048"))
    
    # Namespace & Collection Configs
    DEFAULT_COLLECTION = os.getenv("RAG_DEFAULT_COLLECTION", "default")
    SESSION_MAX_ITEMS = int(os.getenv("RAG_SESSION_MAX_ITEMS", "100"))
    VERSION_CHAIN_MAX_DEPTH = int(os.getenv("RAG_VERSION_CHAIN_MAX", "50"))
    
    # Graph & Context Packing
    GRAPH_EXPAND_DEPTH = int(os.getenv("RAG_GRAPH_EXPAND_DEPTH", "2"))
    RERANK_ENABLED = True
    RERANK_TOP_N = int(os.getenv("RAG_RERANK_TOP_N", "10"))
    CONTEXT_PACK_MAX_TOKENS = int(os.getenv("RAG_CONTEXT_MAX_TOKENS", "4000"))
    CONTEXT_MAX_PER_SOURCE = int(os.getenv("RAG_CONTEXT_MAX_PER_SOURCE", "2"))
    METADATA_RECENCY_WEIGHT = float(os.getenv("RAG_RECENCY_WEIGHT", "0.3"))

    SEARCH_TOP_K = TOP_K
    REASONING_MEMORY_THRESHOLD = float(os.getenv("RAG_REASONING_MEM_THRESHOLD", "0.3"))
    MAX_REASONING_HISTORY = int(os.getenv("RAG_MAX_REASONING_HISTORY", "50"))
    
    # Master (Analysis)
    DEFAULT_MAX_DEPTH = int(os.getenv("BRAIN_MAX_DEPTH", "3"))
    
    # Thresholds
    LOOP_SIMILARITY_THRESHOLD = 0.75
    LOOP_WARNING_THRESHOLD = 0.60

    # Reasoning Keywords
    NEGATION_KEYWORDS = [
        # English
        "no", "not", "but", "however", "contradict", "instead", "refute", "incorrect", "wrong",
        "disagree", "oppose", "negative", "invalid", "untrue", "flawed", "erroneous", "mistaken",
        "paradox", "conflict", "clash", "nullify", "void", "inconsistent", "disprove", "reject", "deny",
        "shouldn't", "wouldn't", "cannot", "don't", "never", "cancel",
        # Turkish
        "değil", "hayır", "fakat", "ancak", "ama", "aksine", "yanlış", "hatalı", "yalan", "geçersiz",
        "uyumsuz", "çelişki", "reddet", "maalesef", "ne yazık ki", "olumsuz", "hata", "kusur",
        "çürüt", "yok say", "geçersiz kıl", "olmaz", "iptal"
    ]
    CONCLUSION_KEYWORDS = [
        # English
        "conclude", "summary", "final", "therefore", "result", "finish", "done", "complete",
        "finally", "ultimately", "conclusively", "wrapping up", "closing", "resolving", "outcome",
        "end", "settled", "decided", "determined", "fixed", "decision", "solution",
        # Turkish
        "sonuç", "özet", "nihai", "tamam", "bitir", "neticede", "sonuçta", "nihayet", "özetle",
        "bağlamak gerekirse", "karar", "kesin", "çözüldü", "netice", "bitiriş", "kapanış", "çözüm"
    ]

    @classmethod
    def setup(cls):
        """Ensure critical directories exist (data, chroma, sqlite)."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        chroma_dir = os.path.join(cls.DATA_DIR, "chroma")
        os.makedirs(chroma_dir, exist_ok=True)
        
        sqlite_dir = os.path.join(cls.DATA_DIR, "sqlite")
        os.makedirs(sqlite_dir, exist_ok=True)
        
        # Brain specific model check
        if cls.MODEL_PATH and not os.path.exists(cls.MODEL_PATH):
            logging.warning(f"Embedding model not found at {cls.MODEL_PATH}. Semantic search will be disabled.")

def validate_project_root(path: Optional[str]) -> str:
    """Standardized project root validation for all tools."""
    if not path:
        raise ValueError("project_root is required.")
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        raise ValueError(f"Project root does not exist: {abs_path}")
    return abs_path
