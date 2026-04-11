import os
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

def register_process_tools(mcp: FastMCP, services: Dict[str, Any], config: Dict[str, Any]):
    """Registers background process management tools."""
    
    process_svc = services["process"]
    paths = config["paths"]

    @mcp.tool()
    async def run_background_command(command: str, project_root: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs a terminal command in the background. 
        Waits 3 seconds to see if it finishes or errors out early.
        Returns a task_id if it continues to run.
        """
        root = project_root or paths["PROJECT_ROOT"] or os.getcwd()
        return await process_svc.run_command(command, root)

    @mcp.tool()
    def get_process_status(task_id: str, tail: int = 50) -> Dict[str, Any]:
        """
        Checks the status and output of a background task.
        Use this to follow progress of a running process.
        """
        return process_svc.get_status(task_id, tail=tail)

    @mcp.tool()
    def stop_process(task_id: str) -> Dict[str, Any]:
        """
        Stops a running background task and all its child processes.
        """
        return process_svc.stop_task(task_id)

    @mcp.tool()
    def list_background_processes() -> List[Dict[str, Any]]:
        """
        Lists all background tasks managed by this server.
        """
        return process_svc.list_tasks()
