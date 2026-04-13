import os
import json
import sys
import platform
import psutil
from fastmcp import FastMCP

def register_diagnostic_tools(mcp: FastMCP, diag_svc, audit_logs_path, memory_path, PROJECT_ROOT, SERVER_HOME):
    @mcp.tool()
    async def get_tool_inventory() -> str:
        """Returns all tools with descriptions and current health status."""
        report = await diag_svc.get_health_report()
        inventory = {
            "System_Health": report["components"],
            "Intelligence & Research": {
                "Tools": ["ask_expert", "list_models", "show_model", "web_search", "search_stackoverflow"],
                "Description": "Local LLM consultation and global knowledge retrieval."
            },
            "Advanced Reasoning": {
                "Tools": ["sequentialthinking", "clear_thinking", "create_plan", "task_mark_step"],
                "Description": "Chain-of-thought analysis and structured plan execution."
            },
            "Unified Lite Memory": {
                "Tools": ["memory_store_fact", "memory_store_user_habit", "memory_retrieve_facts", "memory_index_file", "memory_index_workspace", "memory_search_semantic"],
                "Description": "RAG & Fact system. Facts are auto-indexed semantically."
            },
            "Smart File Operations": {
                "Tools": ["read_file", "write_file", "edit_file", "list_directory", "directory_tree", "search_files", "search_semantic", "validate_syntax"],
                "Description": "File management with syntax validation and recursive search."
            },
            "System & Project Monitoring": {
                "Tools": [
                    "system_info", "get_project_history", 
                    "task_get_active", "simulate_diagnostic_failure", 
                    "check_port", "manage_background_job", "remote_ssh_command"
                ],
                "Description": "Health checks, audit logs, and diagnostic simulations."
            }
        }
        return json.dumps(inventory, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def simulate_diagnostic_failure(component: str) -> str:
        """Simulate a failure for a component (e.g. 'ollama', 'rg') to test Degraded Mode."""
        diag_svc.simulate_failure(component)
        return f"Simulated failure for '{component}'. Run get_tool_inventory or a tool requiring it to see effects."




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

    @mcp.tool()
    async def check_port(port: int) -> str:
        """Check whether a TCP port is in use and which process holds it."""
        result = diag_svc.check_port(port)
        if "error" in result:
            return f"Error: {result['error']}"
        if result["in_use"]:
            return (
                f"Port {port} is IN USE\n"
                f"  PID:     {result['pid']}\n"
                f"  Process: {result['process'] or 'unknown'}\n"
                f"  Status:  {result['status']}"
            )
        return f"Port {port} is free."

