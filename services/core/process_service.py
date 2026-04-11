import asyncio
import os
import signal
import subprocess
import time
import uuid
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque

import psutil
from services.core.logger_service import setup_logger

logger = setup_logger("ProcessService")

class ProcessService:
    """
    Manages background subprocesses with cross-platform support.
    Features:
    - 3-second hybrid wait logic for immediate feedback.
    - Thread-safe live output buffering.
    - Persistent logs in .mcp-master/logs/processes/.
    - Process tree management using psutil.
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.logs_dir = self.data_dir / "logs" / "processes"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Store active processes: task_id -> {process_obj, start_time, command, log_file, buffer, lock}
        self.active_processes: Dict[str, Dict[str, Any]] = {}
        logger.info(f"ProcessService initialized. Logs directory: {self.logs_dir}")

    def _read_stream_sync(self, stream, task_id, log_file):
        """Monitor a stream in a separate thread and write to log file + buffer."""
        # Use a local ref to the buffer and lock
        if task_id not in self.active_processes:
            return
        
        info = self.active_processes[task_id]
        buffer = info["buffer"]
        lock = info["lock"]
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                # Read line by line for better buffer management
                for line in iter(stream.readline, b''):
                    decoded = line.decode('utf-8', errors='replace')
                    f.write(decoded)
                    f.flush()
                    with lock:
                        buffer.append(decoded)
            stream.close()
        except Exception as e:
            logger.error(f"Error reading stream for task {task_id}: {e}")

    async def run_command(self, command: str, project_root: str) -> Dict[str, Any]:
        """
        Runs a command in the background, waits 3 seconds for initial feedback.
        """
        task_id = f"bg_{uuid.uuid4().hex[:8]}"
        log_file = self.logs_dir / f"{task_id}.log"
        
        logger.info(f"Starting background command [{task_id}]: {command}")
        
        try:
            # Create a subprocess using sync Popen
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr into stdout
                cwd=project_root,
                shell=True,
                bufsize=1, # Line buffered
                universal_newlines=False, # Use bytes for the thread reader
                start_new_session=True if os.name != "nt" else False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            )
            
            self.active_processes[task_id] = {
                "process": process,
                "start_time": time.time(),
                "command": command,
                "log_file": log_file,
                "buffer": deque(maxlen=100),
                "lock": threading.Lock()
            }

            # Start the log monitoring thread
            thread = threading.Thread(
                target=self._read_stream_sync,
                args=(process.stdout, task_id, log_file),
                daemon=True
            )
            thread.start()

            # Hybrid Wait: Poll for 3 seconds
            poll_start = time.time()
            
            while time.time() - poll_start < 3.0:
                if process.poll() is not None:
                    # Process finished early
                    exit_code = process.returncode
                    logger.info(f"Task [{task_id}] finished early with code {exit_code}")
                    
                    with self.active_processes[task_id]["lock"]:
                        output = "".join(list(self.active_processes[task_id]["buffer"]))
                    
                    return {
                        "status": "completed",
                        "task_id": task_id,
                        "output": output,
                        "exit_code": exit_code
                    }
                await asyncio.sleep(0.2)

            # Still running after 3 seconds
            logger.info(f"Task [{task_id}] is still running after 3s. Returning intermediate state.")
            with self.active_processes[task_id]["lock"]:
                output = "".join(list(self.active_processes[task_id]["buffer"]))
                
            return {
                "status": "running",
                "task_id": task_id,
                "output": output,
                "message": "Process is still running in background. Use get_process_status to check progress."
            }

        except Exception as e:
            logger.error(f"Failed to start background command: {e}")
            return {"status": "error", "error": str(e)}

    def get_status(self, task_id: str, tail: int = 50) -> Dict[str, Any]:
        """Reads the status and log output for a task."""
        if task_id not in self.active_processes:
            # Check if log file exists
            log_file = self.logs_dir / f"{task_id}.log"
            if not log_file.exists():
                return {"status": "not_found", "message": f"Task {task_id} not found."}
            
            with open(log_file, "r", encoding="utf-8") as rf:
                lines = rf.readlines()
                output = "".join(lines[-tail:])
            return {"status": "completed", "output": output, "message": "Task history retrieved from logs."}

        task_info = self.active_processes[task_id]
        process = task_info["process"]
        
        # Update status
        exit_code = process.poll()
        is_running = exit_code is None
        
        # Use live buffer for recent output
        with task_info["lock"]:
            output = "".join(list(task_info["buffer"])[-tail:])

        return {
            "status": "running" if is_running else "completed",
            "task_id": task_id,
            "output": output,
            "exit_code": exit_code if not is_running else None
        }

    def stop_task(self, task_id: str) -> Dict[str, Any]:
        """Stops the task and its child processes tree."""
        if task_id not in self.active_processes:
            return {"status": "error", "message": "Task not active or not found."}

        task_info = self.active_processes[task_id]
        process = task_info["process"]
        
        try:
            parent = psutil.Process(process.pid)
            # Terminate children first
            children = parent.children(recursive=True)
            for child in children:
                try: child.terminate()
                except: pass
            
            try: parent.terminate()
            except: pass
            
            # Wait a bit then kill if still alive
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            for p in alive:
                try: p.kill()
                except: pass

            logger.info(f"Task [{task_id}] stopped manually.")
            return {"status": "stopped", "task_id": task_id}
        except psutil.NoSuchProcess:
            return {"status": "error", "message": "Process already terminated."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Lists all tracked processes."""
        summary = []
        for task_id, info in self.active_processes.items():
            exit_code = info["process"].poll()
            summary.append({
                "task_id": task_id,
                "command": info["command"],
                "status": "running" if exit_code is None else "completed",
                "start_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info["start_time"]))
            })
        return summary
