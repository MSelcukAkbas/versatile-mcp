import os
import json
import subprocess
from typing import List, Dict, Any, Optional
from services.core.logger_service import setup_logger

logger = setup_logger("SearchEngine")

class SearchEngine:
    """Orchestrates fast text searches using Ripgrep binary."""
    
    def __init__(self, bin_service: Any, project_root: str):
        self.bin_service = bin_service
        self.project_root = project_root

    def search_files(self, pattern: str, directory: str = ".") -> List[str]:
        """Search for files matching a pattern (case-insensitive)."""
        matches = []
        target_dir = os.path.join(self.project_root, directory)
        for root, _, files in os.walk(target_dir):
            for name in files:
                if pattern.lower() in name.lower():
                    matches.append(os.path.relpath(os.path.join(root, name), self.project_root))
        return matches

    def search_content(self, query: str, directory: str = ".") -> List[Dict[str, Any]]:
        """LLM-Optimized content search using Ripgrep."""
        rg_path = self.bin_service.get_binary_path("rg")
        if not rg_path: return [{"error": "Ripgrep not found."}]

        target_dir = os.path.join(self.project_root, directory)
        try:
            cmd = [str(rg_path), "--json", "-i", query, target_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            
            matches = []
            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        payload = data.get("data")
                        abs_path = payload.get("path", {}).get("text")
                        matches.append({
                            "file": os.path.relpath(abs_path, self.project_root),
                            "line": payload.get("line_number"),
                            "abs_path": abs_path
                        })
                except: continue
            return matches[:50]
        except Exception as e:
            return [{"error": str(e)}]
