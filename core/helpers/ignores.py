import os
import logging
from typing import List, Optional, Set
import pathspec

# Use a generic logger or allow injection
logger = logging.getLogger("CoreIgnoreService")

class IgnoreService:
    """
    Unified Service to handle file/directory ignore patterns using .gitignore syntax.
    Supports multi-gitignore discovery and system-level baseline ignores.
    """
    
    def __init__(self, project_root: str, default_ignore_path: Optional[str] = None):
        self.project_root = os.path.abspath(project_root)
        self.default_ignore_path = default_ignore_path
        self.spec: Optional[pathspec.PathSpec] = None
        self.refresh()

    def refresh(self):
        """Reload patterns from default file and all project-level .gitignore files."""
        all_patterns = []
        
        # 1. System Baseline Ignores
        all_patterns.extend([
            ".git/",
            ".mcp-master/",
            ".versatile-brain/",
            ".versatile-mcp/",
            "__pycache__/",
            "*.pyc",
            "node_modules/",
            ".venv/",
            "venv/",
            ".gemini/",
            ".antigravity/"
        ])

        # 2. Load global baseline if provided
        if self.default_ignore_path and os.path.exists(self.default_ignore_path):
            try:
                with open(self.default_ignore_path, 'r', encoding='utf-8') as f:
                    all_patterns.extend(f.readlines())
            except Exception as e:
                logger.error(f"Failed to load baseline ignores: {e}")

        # 3. Dynamic Multi-Gitignore Discovery
        try:
            for root, dirs, files in os.walk(self.project_root, topdown=True):
                # Optimization: skip known massive ignored folders during search
                dirs[:] = [d for d in dirs if d not in [".git", "node_modules", ".venv", "venv", "dist", "build"]]
                
                if ".gitignore" in files:
                    g_path = os.path.join(root, ".gitignore")
                    rel_dir = os.path.relpath(root, self.project_root).replace("\\", "/")
                    prefix = "" if rel_dir == "." else f"{rel_dir}/"
                    
                    try:
                        with open(g_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    all_patterns.append(f"{prefix}{line}")
                    except Exception as e:
                        logger.error(f"Failed to load {g_path}: {e}")
        except Exception as e:
            logger.error(f"Error during .gitignore discovery: {e}")

        # 4. Final Processing
        clean_patterns = [
            line.strip() for line in all_patterns 
            if line.strip() and not line.strip().startswith('#')
        ]

        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', clean_patterns)
        logger.debug(f"IgnoreService initialized with {len(clean_patterns)} patterns.")

    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """Check if a relative path matches any ignore pattern."""
        if not self.spec:
            return False
            
        normalized_path = rel_path.replace("\\", "/")
        if is_dir and not normalized_path.endswith("/"):
            normalized_path += "/"
            
        return self.spec.match_file(normalized_path)

    def get_spec(self):
        """Returns the pathspec object for direct use (e.g. in Scanners)."""
        return self.spec
