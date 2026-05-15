import json
import logging
from core.config import Config as BrainConfig
from fastmcp import FastMCP

logger = logging.getLogger("Versatile-Brain")

def register_workspace_tools(mcp: FastMCP, memory_svc, ignore_svc, analyzer_svc, validate_project_root):
    
    @mcp.tool()
    async def workspace_summary(project_root: str, max_depth: int = None) -> str:
        """
        Generates a comprehensive architectural summary of the workspace.
        This tool analyzes the project structure to provide insights into language distribution, 
        file statistics, top-level directories, and recently modified files.
        
        Use this tool at the beginning of a session to understand the project's technology stack 
        and overall organization before diving into specific code files.
        
        CRITICAL: 'project_root' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') to accurately 
        map the file system and respect project-specific .gitignore rules.
        
        Args:
            project_root: The full ABSOLUTE path to the project root directory. REQUIRED.
            max_depth: Maximum directory depth to scan (default: 3). Higher values provide more detail but take longer.
        """
        project_root = validate_project_root(project_root)
        depth = max_depth or BrainConfig.DEFAULT_MAX_DEPTH
        analysis = analyzer_svc.analyze(project_root, max_depth=depth)
        return json.dumps(analysis, indent=2, ensure_ascii=False)
