import os
import logging
from pathlib import Path
from typing import Optional

class Config:
    """Unified configuration for all Versatile-Mcp servers."""
    
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

    SEARCH_TOP_K = int(os.getenv("BRAIN_SEARCH_TOP_K", "5"))
    REASONING_MEMORY_THRESHOLD = float(os.getenv("BRAIN_REASONING_THRESHOLD", "0.4"))
    MAX_REASONING_HISTORY = int(os.getenv("BRAIN_MAX_REASONING_HISTORY", "20"))
    
    # Master (Analysis)
    DEFAULT_MAX_DEPTH = int(os.getenv("BRAIN_MAX_DEPTH", "3"))
    
    # Thresholds
    LOOP_SIMILARITY_THRESHOLD = 0.75
    LOOP_WARNING_THRESHOLD = 0.65

    # Reasoning Keywords
    NEGATION_KEYWORDS = [
        # English
        "no", "not", "but", "however", "contradict", "instead", "refute", "incorrect", "wrong",
        "disagree", "oppose", "negative", "invalid", "untrue", "flawed", "erroneous", "mistaken",
        "paradox", "conflict", "clash", "nullify", "void", "inconsistent", "disprove", "reject", "deny",
        # Turkish
        "değil", "hayır", "fakat", "ancak", "ama", "aksine", "yanlış", "hatalı", "yalan", "geçersiz",
        "uyumsuz", "çelişki", "reddet", "maalesef", "ne yazık ki", "olumsuz", "hata", "kusur",
        "çürüt", "yok say", "geçersiz kıl"
    ]
    CONCLUSION_KEYWORDS = [
        # English
        "conclude", "summary", "final", "therefore", "result", "finish", "done", "complete",
        "finally", "ultimately", "conclusively", "wrapping up", "closing", "resolving", "outcome",
        "end", "settled", "decided", "determined", "fixed",
        # Turkish
        "sonuç", "özet", "nihai", "tamam", "bitir", "neticede", "sonuçta", "nihayet", "özetle",
        "bağlamak gerekirse", "karar", "kesin", "çözüldü", "netice", "bitiriş", "kapanış"
    ]

    @classmethod
    def setup(cls):
        """Ensure critical directories exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
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
