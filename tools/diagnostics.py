import os
import json
import sys
import platform
import psutil
from fastmcp import FastMCP
from resources.config.settings import PROJECT_ROOT, PROJECT_ID

def register_diagnostic_tools(mcp: FastMCP, diag_svc, audit_logs_path, memory_path, PROJECT_ROOT, SERVER_HOME):
    @mcp.tool()
    async def get_tool_inventory() -> str:
        """Returns all tools with descriptions and current health status dynamically."""
        report = await diag_svc.get_health_report()
        # LIVE TOOL DISCOVERY
        live_tools = await mcp.list_tools()
        tool_names = {t.name for t in live_tools}
        
        groups = {
            "Intelligence & Research": ["ask_expert", "list_models", "show_model", "web_search", "search_stackoverflow"],
            "Advanced Reasoning": ["sequentialthinking", "create_plan", "task_mark_step"],
            "Unified Lite Memory": ["memory_store_fact", "memory_store_user_preference", "memory_retrieve_facts", "memory_index_file", "memory_index_workspace", "memory_forget"],
            "Smart File Operations": ["read_file", "write_file", "multi_replace_file_content", "list_directory_with_sizes", "directory_tree", "search_files", "search_semantic_memory", "validate_syntax"],
            "System & Project Monitoring": [
                "system_info", "get_project_history", "workspace_summary",
                "task_get_active", 
                "check_port", "manage_background_job", "remote_ssh_command"
            ]
        }
        
        inventory = {"System_Health": report["components"]}
        assigned_tools = set()
        
        for group_name, members in groups.items():
            # Only include if tool actually exists in live_tools
            active_members = [m for m in members if m in tool_names]
            if active_members:
                inventory[group_name] = {
                    "Tools": active_members,
                    "Description": self_infer_desc(group_name)
                }
                assigned_tools.update(active_members)
                
        # Handle New/Unassigned Tools automatically
        unassigned = [t for t in tool_names if t not in assigned_tools]
        if unassigned:
            inventory["Newly Discovered / Extensions"] = {
                "Tools": unassigned,
                "Description": "Dynamically detected tools without an explicit category."
            }
            
        return json.dumps(inventory, indent=2, ensure_ascii=False)

    def self_infer_desc(group: str) -> str:
        descs = {
            "Intelligence & Research": "Local LLM consultation and global knowledge retrieval.",
            "Advanced Reasoning": "Chain-of-thought analysis and structured plan execution.",
            "Unified Lite Memory": "RAG & Fact system. Facts are auto-indexed semantically.",
            "Smart File Operations": "High-performance file management with atomic multi-block edits.",
            "System & Project Monitoring": "Deep workspace analysis, health checks, and diagnostics."
        }
        return descs.get(group, "Miscellaneous operations.")


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

