import asyncio
import time
from typing import Dict, Any, List, Optional
from servers.master.services.core.logger_service import setup_logger


logger = setup_logger("DiagnosticService")

class DiagnosticService:
    """Consolidated health monitoring for all Master MCP dependencies."""
    def __init__(self, bin_svc):
        self.bin = bin_svc
        
        # Cache management
        self._last_check_time = 0
        self._cache_duration = 180
        self._health_cache = {}
        self._simulated_failures = set()

    async def get_health_report(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Generates a health report of current binary dependencies."""
        now = time.time()
        if not force_refresh and (now - self._last_check_time < self._cache_duration):
            return self._health_cache

        bin_results = self.bin.check_all_bins()
        
        self._health_cache = {
            "timestamp": now,
            "components": {
                "binaries": {
                    "status": "Online" if all(bin_results.values()) else "Degraded",
                    "details": bin_results
                }
            }
        }
        self._last_check_time = now
        return self._health_cache

    async def check_tool_dependency(self, tool_name: str) -> Optional[str]:
        """Checks if a specific tool has its required binary dependencies installed."""
        report = await self.get_health_report()
        components = report.get("components", {})
        
        # File tools dependency (specific binaries)
        bin_details = components["binaries"]["details"]
        mapping = {
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

    def check_port(self, port: int) -> Dict[str, Any]:
        """Return whether a TCP port is in use and which process holds it."""
        try:
            import psutil
        except ImportError:
            return {"error": "psutil not installed. Run: pip install psutil"}

        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port:
                pid = conn.pid
                proc_name = None
                if pid:
                    try:
                        proc_name = psutil.Process(pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                return {
                    "port": port,
                    "in_use": True,
                    "pid": pid,
                    "process": proc_name,
                    "status": conn.status,
                }
        return {"port": port, "in_use": False, "pid": None, "process": None}

    async def find_process(self, name: str) -> List[Dict[str, Any]]:
        """Find running processes whose name contains *name* (case-insensitive)."""
        return await asyncio.to_thread(self._sync_find_process, name)

    def _sync_find_process(self, name: str) -> List[Dict[str, Any]]:
        try:
            import psutil
        except ImportError:
            return [{"error": "psutil not installed. Run: pip install psutil"}]

        results = []
        needle = name.lower()
        for proc in psutil.process_iter(["pid", "name", "status", "cmdline"]):
            try:
                if needle in (proc.info["name"] or "").lower():
                    results.append({
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "status": proc.info["status"],
                        "cmdline": " ".join(proc.info["cmdline"] or [])[:200],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results
