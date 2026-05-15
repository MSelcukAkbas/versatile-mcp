import os
import asyncio
import asyncssh
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from fastmcp import FastMCP

# Internal job/connection states
_jobs: Dict[str, Dict[str, Any]] = {}
_connection_cache = {}

class RemoteExecutionError(Exception):
    pass

def register_remote_tools(mcp: FastMCP, root_path: str):
    """Registers all Remote Execution tools to the unified MCP instance."""
    
    HISTORY_FILE = os.path.join(root_path, "servers", "remote", "history.jsonl")

    def _log_execution(data: Dict[str, Any]):
        log_entry = {"timestamp": datetime.now().isoformat(), **data}
        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Logging error: {e}", file=sys.stderr)

    async def get_connection(host: str, user: str, password: str = None):
        cache_key = f"{user}@{host}"
        if cache_key in _connection_cache:
            conn = _connection_cache[cache_key]
            try:
                await conn.run("true", timeout=2)
                return conn
            except:
                del _connection_cache[cache_key]
        try:
            conn = await asyncssh.connect(host, username=user, password=password, known_hosts=None)
            _connection_cache[cache_key] = conn
            return conn
        except Exception as e:
            raise RemoteExecutionError(f"Connection failed: {str(e)}")

    async def _background_worker(job_id: str, host: str, user: str, password: str, command: str, timeout: int):
        try:
            _jobs[job_id]["status"] = "running"
            conn = await get_connection(host, user, password)
            result = await conn.run(command, timeout=timeout)
            _jobs[job_id].update({
                "status": "success" if result.exit_status == 0 else "failed",
                "exit_code": result.exit_status,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "completed_at": datetime.now().isoformat()
            })
            _log_execution({"job_id": job_id, "host": host, "user": user, "command": command, "status": _jobs[job_id]["status"]})
        except Exception as e:
            _jobs[job_id].update({"status": "error", "message": str(e), "completed_at": datetime.now().isoformat()})

    @mcp.tool()
    async def ssh_execute(host: str, user: str, password: str, command: str, timeout: int = 60, run_in_background: bool = False) -> str:
        """
        Executes a command on a remote server using a high-performance native SSH engine. 
        Supports both synchronous execution and asynchronous background jobs. 
        Ideal for remote deployment, maintenance, system monitoring, or automated patching.
        
        Args:
            host: Remote server address (IP or domain).
            user: SSH username for authentication.
            password: Password for authentication. (Note: Future updates will support SSH keys).
            command: The command line string to execute on the remote machine.
            timeout: Execution timeout in seconds (default: 60).
            run_in_background: If True, returns a job_id immediately and runs in background.
        """
        if not run_in_background:
            try:
                conn = await get_connection(host, user, password)
                result = await conn.run(command, timeout=timeout)
                response = {"status": "success" if result.exit_status == 0 else "failed", "exit_code": result.exit_status, "stdout": result.stdout, "stderr": result.stderr}
                _log_execution({"host": host, "user": user, "command": command, "status": response["status"], "exit_code": response["exit_code"]})
                return json.dumps(response, indent=2, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        else:
            job_id = f"job-{uuid.uuid4().hex[:8]}"
            _jobs[job_id] = {"id": job_id, "status": "queued", "command": command, "host": host, "started_at": datetime.now().isoformat()}
            asyncio.create_task(_background_worker(job_id, host, user, password, command, timeout))
            return json.dumps({"status": "queued_in_background", "job_id": job_id}, indent=2)

    @mcp.tool()
    async def check_job_status(job_id: str) -> str:
        """
        Checks the status, logs, and execution results of a background SSH job started with 'ssh_execute'. 
        Use this to monitor long-running tasks or retrieve results from non-blocking executions. 
        Returns exit codes, stdout, and stderr once the job reaches 'success' or 'failed' state.
        
        Args:
            job_id: The unique identifier returned by ssh_execute(run_in_background=True).
        """
        return json.dumps(_jobs.get(job_id, {"error": "Job not found"}), indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_ssh_history(limit: int = 20) -> str:
        """
        Retrieves a structured audit log of past SSH executions, including timestamps, targets, commands, and final status. 
        Useful for tracking remote changes, auditing user actions, and debugging repetitive connection patterns.
        
        Args:
            limit: Maximum number of recent log entries to return (default: 20).
        """
        if not os.path.exists(HISTORY_FILE): return "No history."
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.dumps([json.loads(line) for line in f.readlines()[-limit:]], indent=2, ensure_ascii=False)
