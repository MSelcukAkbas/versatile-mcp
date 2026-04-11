import json
import os
from typing import Optional, Dict, List
from fastmcp import FastMCP

def register_git_tools(mcp: FastMCP, git_svc, diag_svc):
    @mcp.tool()
    async def git_push(commit_message: str, branch: Optional[str] = None) -> str:
        """
        Stage all changes, commit, and push using local Git CLI.
        Cleans up VS Code 'Source Control' UI by performing a local commit.
        """
        try:
            # Diagnostic check
            err = await diag_svc.check_tool_dependency("git_push")
            if err: return err
            
            # We assume the project root is the current working directory for git
            cwd = os.getcwd() 
            result = git_svc.push(cwd, commit_message, branch)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def git_pull(branch: Optional[str] = None) -> str:
        """
        Sync local repository with remote using local Git CLI (git pull).
        """
        try:
            err = await diag_svc.check_tool_dependency("git_pull")
            if err: return err
            
            cwd = os.getcwd()
            result = git_svc.pull(cwd, branch)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def git_diff(base: str = "HEAD") -> str:
        """
        Show changes between commits, commit and working tree, etc.
        """
        try:
            err = await diag_svc.check_tool_dependency("git_diff")
            if err: return err
            
            cwd = os.getcwd()
            result = git_svc.diff(cwd, base)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def git_status() -> str:
        """
        Show the working tree status (short format).
        """
        try:
            err = await diag_svc.check_tool_dependency("git_status")
            if err: return err
            
            cwd = os.getcwd()
            status = git_svc.get_status(cwd)
            return status if status else "Working tree clean."
        except Exception as e:
            return f"Error: {str(e)}"
