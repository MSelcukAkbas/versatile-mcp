import asyncio
import time
from typing import Dict, Any, List, Optional
from services.core.logger_service import setup_logger

logger = setup_logger("DiagnosticService")

class DiagnosticService:
<<<<<<< HEAD
    """Consolidated health monitoring for all Master MCP dependencies."""
    
=======
>>>>>>> 6018f667c25b3f3db7fdd2593e7e548fc6bcaffc
    def __init__(self, ollama_svc, bin_svc, github_svc=None):
        self.ollama = ollama_svc
        self.bin = bin_svc
        self.github = github_svc
<<<<<<< HEAD
        
        # Cache management
=======
>>>>>>> 6018f667c25b3f3db7fdd2593e7e548fc6bcaffc
        self._last_check_time = 0
        self._cache_duration = 180
        self._health_cache = {}
        self._simulated_failures = set()

    async def get_health_report(self, force_refresh: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force_refresh and (now - self._last_check_time < self._cache_duration):
            return self._health_cache

        ollama_ok = await self.ollama.is_ready() if "ollama" not in self._simulated_failures else False
        bin_results = self.bin.check_all_bins()
        
        github_status = {"status": "Offline", "details": "GitHub service not initialized"}
        if self.github:
            github_status = self.github.get_status()

        # Git Check
        git_status = {"status": "Offline", "details": "Git binary not found"}
        if self.bin.is_tool_available("git"):
            git_status = {"status": "Online", "details": "Git CLI available"}

        self._health_cache = {
            "timestamp": now,
            "components": {
<<<<<<< HEAD
                "ollama": {
                    "status": "Online" if ollama_ok else "Offline",
                    "details": "Local Ollama service responsive" if ollama_ok else "Service unreachable on localhost:11434"
                },
                "binaries": {
                    "status": "Online" if all(bin_results.values()) else "Degraded",
                    "details": bin_results
                },
                "git": git_status
=======
                "ollama": {"status": "Online" if ollama_ok else "Offline", "details": "Ollama service status"},
                "binaries": {"status": "Online" if all(bin_results.values()) else "Degraded", "details": bin_results},
                "github": github_status
>>>>>>> 6018f667c25b3f3db7fdd2593e7e548fc6bcaffc
            }
        }
        self._last_check_time = now
        return self._health_cache

    async def check_tool_dependency(self, tool_name: str) -> Optional[str]:
        report = await self.get_health_report()
        components = report.get("components", {})
        
        github_tools = ["github_api_push", "github_api_diff", "github_api_sync", "github_manage_issues", "github_api_get_file"]
        if tool_name in github_tools:
            if components["github"]["status"] != "Online":
                return f"GitHub Error: {components['github']['details']}. Please check token permissions."
        
<<<<<<< HEAD
        # Git tools dependency
        git_tools = ["git_push", "git_pull", "git_diff", "git_status"]
        if tool_name in git_tools:
            if components["git"]["status"] != "Online":
                return "Git binary is not found on this system. Please install Git to use these tools."

        # File tools dependency (specific binaries)
        bin_details = components["binaries"]["details"]
        mapping = {
            "search_files": "rg",
            "search_content": "rg",
            "validate_syntax": ["ruff", "oxlint", "biome"]
        }
        
        if tool_name in mapping:
            dep = mapping[tool_name]
            if isinstance(dep, list):
                missing = [d for d in dep if not bin_details.get(d, True)]
                if missing:
                    return f"Missing required binaries for full validation: {', '.join(missing)}"
            elif not bin_details.get(dep, True):
                return f"The '{dep}' binary is missing. Please check your bin/ directory."
=======
        if tool_name in ["ask_expert", "list_models"]: 
             if components["ollama"]["status"] != "Online":
                return "Ollama service is unreachable."
>>>>>>> 6018f667c25b3f3db7fdd2593e7e548fc6bcaffc
                
        return None
