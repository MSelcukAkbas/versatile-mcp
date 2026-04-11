import asyncio
import time
from typing import Dict, Any, List, Optional
from services.core.logger_service import setup_logger

logger = setup_logger("DiagnosticService")

class DiagnosticService:
    def __init__(self, ollama_svc, bin_svc, github_svc=None):
        self.ollama = ollama_svc
        self.bin = bin_svc
        self.github = github_svc
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

        self._health_cache = {
            "timestamp": now,
            "components": {
                "ollama": {"status": "Online" if ollama_ok else "Offline", "details": "Ollama service status"},
                "binaries": {"status": "Online" if all(bin_results.values()) else "Degraded", "details": bin_results},
                "github": github_status
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
        
        if tool_name in ["ask_expert", "list_models"]: 
             if components["ollama"]["status"] != "Online":
                return "Ollama service is unreachable."
                
        return None
