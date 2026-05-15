import os
from typing import List, Dict, Any, Optional

class FileScanner:
    """Scans and categorizes files in a workspace."""
    
    def __init__(self, ignore_spec):
        self.ignore_spec = ignore_spec

    def scan(self, root: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        results = []
        base_depth = root.count(os.sep)
        
        for dirpath, dirnames, filenames in os.walk(root):
            # Check depth
            depth = dirpath.count(os.sep) - base_depth
            if depth >= max_depth:
                dirnames[:] = [] # Stop recursion
                continue

            # Filtering ignored directories
            dirnames[:] = [d for d in dirnames if not self.ignore_spec.match_file(os.path.join(dirpath, d))]
            
            for f in filenames:
                full = os.path.join(dirpath, f)
                rel_path = os.path.relpath(full, root)
                if not self.ignore_spec.match_file(rel_path):
                    try:
                        stat = os.stat(full)
                        results.append({
                            "path": rel_path,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "type": os.path.splitext(f)[1]
                        })
                    except OSError:
                        pass
        return results
