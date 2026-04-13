import os
import json
import sys
import platform
import psutil
from fastmcp import FastMCP
from resources.config.settings import PROJECT_ROOT, PROJECT_ID

def register_diagnostic_tools(mcp: FastMCP, diag_svc, audit_logs_path, memory_path, PROJECT_ROOT, SERVER_HOME):


    @mcp.tool()
    async def system_info() -> str:
        """
        Return detailed system information about the machine running the MCP server.
        Includes OS, platform, CPU, RAM, Python version, and working directory.
        Use this to understand the execution environment before running platform-specific commands.
        """
        try:
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(PROJECT_ROOT)
            info = {
                "os": platform.system(),                          # e.g. "Windows" / "Linux" / "Darwin"
                "os_version": platform.version(),
                "os_release": platform.release(),
                "machine": platform.machine(),                     # e.g. "AMD64" / "x86_64"
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": sys.version,
                "cpu_count": os.cpu_count(),
                "ram_total_gb": round(ram.total / 1e9, 2),
                "ram_available_gb": round(ram.available / 1e9, 2),
                "ram_used_percent": ram.percent,
                "disk_total_gb": round(disk.total / 1e9, 2),
                "disk_free_gb": round(disk.free / 1e9, 2),
                "disk_used_percent": disk.percent,
                "cwd": os.getcwd(),
                "active_project_root": PROJECT_ROOT,
                "active_project_id": PROJECT_ID,
                "shell": os.environ.get("SHELL") or os.environ.get("ComSpec", "unknown"),
                "is_windows": platform.system() == "Windows",
                "is_linux": platform.system() == "Linux",
                "is_mac": platform.system() == "Darwin",
            }
            return json.dumps(info, indent=2, ensure_ascii=False)
        except Exception as e:
            # Fallback if psutil not available
            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "python_version": sys.version,
                "cwd": os.getcwd(),
                "is_windows": platform.system() == "Windows",
                "is_linux": platform.system() == "Linux",
                "is_mac": platform.system() == "Darwin",
                "note": f"Extended info unavailable: {str(e)}"
            }
            return json.dumps(info, indent=2, ensure_ascii=False)

    # --- Feature: Process & Port Inspector ---


