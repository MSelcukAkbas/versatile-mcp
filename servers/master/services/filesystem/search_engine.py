import os
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from servers.master.services.core.logger_service import setup_logger

logger = setup_logger("SearchEngine")

class SearchEngine:
    """Orchestrates fast text searches using Ripgrep binary with JSON output support."""
    
    def __init__(self, bin_service: Any, project_root: str):
        self.bin_service = bin_service
        self.project_root = project_root

    async def search_content(self, query: str, directory: str = ".", includes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """LLM-Optimized content search using Ripgrep."""
        return await asyncio.to_thread(self._sync_search_content, query, directory, includes)

    def _sync_search_content(self, query: str, directory: str = ".", includes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        rg_path = self.bin_service.get_binary_path("rg")
        if not rg_path: 
            return [{"error": "Ripgrep binary (rg) not found in the search path."}]

        target_dir = os.path.join(self.project_root, directory)
        try:
            # --json: enables machine-readable output
            # --fixed-strings: treats query as literal (can be changed if regex needed)
            cmd = [str(rg_path), "--json", query, target_dir]
            
            if includes:
                for inc in includes:
                    cmd.extend(["-g", inc])
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding="utf-8", 
                errors="replace"
            )
            
            stdout, stderr = process.communicate()
            
            matches = []
            for line in stdout.splitlines():
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        payload = data.get("data")
                        abs_path = payload.get("path", {}).get("text")
                        line_content = payload.get("lines", {}).get("text", "").strip()
                        
                        matches.append({
                            "file": os.path.relpath(abs_path, self.project_root).replace("\\", "/"),
                            "line": payload.get("line_number"),
                            "match": line_content,
                            "abs_path": abs_path
                        })
                except: 
                    continue
                
                # Limit results to prevent token overflow but keep it useful
                if len(matches) >= 100:
                    break
                    
            return matches
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [{"error": str(e)}]
