import os
from typing import List, Optional
import pathspec
from services.core.logger_service import setup_logger

logger = setup_logger("IgnoreService")

class IgnoreService:
    """Service to handle file/directory ignore patterns using .gitignore syntax."""
    
    def __init__(self, default_ignore_path: str, project_root: str):
        self.default_ignore_path = default_ignore_path
        self.project_root = project_root
        self.spec: Optional[pathspec.PathSpec] = None
        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from default file and project-specific .gitignore."""
        all_patterns = []
        
        # 1. Load forced system ignores
        all_patterns.extend([
            ".git/",
            ".mcp-master/",
            "__pycache__/",
            "*.pyc"
        ])

        # 2. Load default global ignore file
        if os.path.exists(self.default_ignore_path):
            try:
                with open(self.default_ignore_path, 'r', encoding='utf-8') as f:
                    all_patterns.extend(f.readlines())
                logger.info(f"Loaded default ignore patterns from {self.default_ignore_path}")
            except Exception as e:
                logger.error(f"Failed to load default ignores: {e}")

        # 3. Load project-specific .gitignore
        gitignore_path = os.path.join(self.project_root, ".gitignore")
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    all_patterns.extend(f.readlines())
                logger.info(f"Loaded project-specific ignores from {gitignore_path}")
            except Exception as e:
                logger.error(f"Failed to load project .gitignore: {e}")

        # 4. Filter empty lines and comments
        clean_patterns = [
            line.strip() for line in all_patterns 
            if line.strip() and not line.strip().startswith('#')
        ]

        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', clean_patterns)
        logger.info(f"IgnoreService initialized with {len(clean_patterns)} active patterns.")

    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """
        Check if a relative path (from project root) matches any ignore pattern.
        """
        if not self.spec:
            return False
            
        # Normalize path for pathspec
        normalized_path = rel_path.replace("\\", "/")
        
        # Git patterns often require a trailing slash for directory matches
        if is_dir and not normalized_path.endswith("/"):
            normalized_path += "/"
            
        return self.spec.match_file(normalized_path)

    def refresh(self):
        """Reload patterns from files."""
        self._load_patterns()
