import json
from fastmcp import FastMCP

def register_intelligence_tools(mcp: FastMCP, memory_svc, analyzer_svc, ignore_svc, validate_project_root):
    """
    Intelligence tools are now deprecated in favor of atomic workspace and memory tools.
    This module remains for future specialized analytical tools that don't overlap with core services.
    """
    pass
