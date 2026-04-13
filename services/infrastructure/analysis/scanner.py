import os
import pathlib
from typing import List, Dict, Any, Optional
from services.core.logger_service import setup_logger

logger = setup_logger("Analysis.Scanner")

class MetadataScanner:
    """Fast recursive scanner for project metadata."""
    
    def __init__(self, project_root: pathlib.Path, ignore_svc: Optional[Any] = None):
        self.project_root = project_root
        self.ignore_svc = ignore_svc

    def scan(self, max_depth: int = 5) -> List[Dict[str, Any]]:
        results = []
        for root, dirs, files in os.walk(self.project_root):
            rel_root = os.path.relpath(root, self.project_root)
            depth = 0 if rel_root == "." else len(rel_root.split(os.sep))
            if depth > max_depth: continue

            if self.ignore_svc:
                dirs[:] = [d for d in dirs if not self.ignore_svc.is_ignored(os.path.join(rel_root, d), is_dir=True)]
                files = [f for f in files if not self.ignore_svc.is_ignored(os.path.join(rel_root, f), is_dir=False)]

            for file in files:
                file_path = pathlib.Path(root) / file
                ext = file_path.suffix.lower()
                try:
                    stat = file_path.stat()
                    results.append({
                        "path": os.path.relpath(file_path, self.project_root).replace("\\", "/"),
                        "abs_path": str(file_path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "extension": ext
                    })
                except: continue
        return results

    @staticmethod
    def get_language(ext: str) -> str:
        map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.md': 'markdown', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
            '.html': 'html', '.css': 'css', '.sql': 'sql', '.sh': 'bash'
        }
        return map.get(ext, 'text')
