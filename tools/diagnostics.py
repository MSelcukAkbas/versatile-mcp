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
                "Tools": ["read_file", "write_file", "edit_file", "list_directory", "directory_tree", "search_files", "validate_syntax"],
                "Description": "File management with syntax validation and recursive search."
            },
            "System & Project Monitoring": {
                "Tools": ["system_info", "debug_paths", "list_audit_logs", "get_project_history", "task_get_active", "simulate_diagnostic_failure"],
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
    async def list_audit_logs() -> str:
        """List available audit log files (.jsonl) with entry counts."""
        try:
            if not os.path.exists(audit_logs_path):
                return "No audit logs directory found."
            
            files = sorted(
                [f for f in os.listdir(audit_logs_path) if f.endswith(".jsonl")],
                reverse=True
            )
            if not files:
                return "No audit log files found yet (.jsonl). Logs are created on first tool call."
            
            lines = ["Audit Logs (JSON Lines format):"]
            for fname in files:
                fpath = os.path.join(audit_logs_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        count = sum(1 for line in f if line.strip())
                    size_kb = os.path.getsize(fpath) / 1024
                    lines.append(f"  {fname}  ({count} entries, {size_kb:.1f} KB)")
                except Exception:
                    lines.append(f"  {fname}  (unreadable)")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing audit logs: {str(e)}"

    @mcp.tool()
    async def debug_paths() -> str:
        """Show internal system paths for debugging."""
        return f"SERVER_HOME: {SERVER_HOME}\nPROJECT_ROOT: {PROJECT_ROOT}\nMemory: {memory_path}\nAudit: {audit_logs_path}"

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

    @mcp.tool()
    async def find_process(name: str) -> str:
        """Find running processes whose name contains *name* (case-insensitive)."""
        results = diag_svc.find_process(name)
        if not results:
            return f"No running process found matching '{name}'."
        if "error" in results[0]:
            return f"Error: {results[0]['error']}"
        lines = [f"Found {len(results)} process(es) matching '{name}':"]
        for p in results:
            lines.append(
                f"  PID {p['pid']}  [{p['status']}]  {p['name']}"
                + (f"\n    cmd: {p['cmdline']}" if p["cmdline"] else "")
            )
        return "\n".join(lines)
