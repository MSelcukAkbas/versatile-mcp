import asyncio
import time
from typing import Dict, Any, List, Optional
from services.core.logger_service import setup_logger

logger = setup_logger("DiagnosticService")

class DiagnosticService:
    """Consolidated health monitoring for all Master MCP dependencies."""
    
    def __init__(self, ollama_svc, bin_svc, github_svc=None):
        self.ollama = ollama_svc
        self.bin = bin_svc
        self.github = github_svc
        
        # Cache management
        self._last_check_time = 0
        self._cache_duration = 180  # 3 minutes as requested
        self._health_cache = {}
        
        # Test / Simulation Mode
        self._simulated_failures = set()

    def simulate_failure(self, component: str):
        """Simulate a component failure for testing purposes."""
        self._simulated_failures.add(component)
        self._last_check_time = 0 # Force refresh

    def clear_simulations(self):
        """Clear all simulated failures."""
        self._simulated_failures.clear()
        self._last_check_time = 0

    async def get_health_report(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch consolidated health report with caching."""
        now = time.time()
        if not force_refresh and (now - self._last_check_time < self._cache_duration):
            return self._health_cache

        logger.info("Refreshing system health diagnostics...")
        
        # Ollama Check
        ollama_ok = False
        if "ollama" not in self._simulated_failures:
            ollama_ok = await self.ollama.is_ready()
        
        # Binaries Check
        bin_results = self.bin.check_all_bins()
        # Apply simulations to bins if any
        for comp in self._simulated_failures:
            if comp in bin_results:
                bin_results[comp] = False

        # Git Check
        git_status = {"status": "Offline", "details": "Git binary not found"}
        if self.bin.is_tool_available("git"):
            git_status = {"status": "Online", "details": "Git CLI available"}

        self._health_cache = {
            "timestamp": now,
            "components": {
                "ollama": {
                    "status": "Online" if ollama_ok else "Offline",
                    "details": "Local Ollama service responsive" if ollama_ok else "Service unreachable on localhost:11434"
                },
                "binaries": {
                    "status": "Online" if all(bin_results.values()) else "Degraded",
                    "details": bin_results
                },
                "git": git_status
            }
        }
        
        self._last_check_time = now
        return self._health_cache

    async def check_tool_dependency(self, tool_name: str) -> Optional[str]:
        """
        Check if a specific tool's dependency is met.
        Returns an error message if missing, None if OK.
        """
        report = await self.get_health_report()
        components = report.get("components", {})
        
        # Intelligence tools dependency
        if tool_name in ["ask_expert", "list_models", "show_model"]:
            if components["ollama"]["status"] != "Online":
                return "The local Ollama service is unreachable. Please ensure Ollama is running on your machine."
        
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
                
        return None
