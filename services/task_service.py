import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from services.logger_service import setup_logger

logger = setup_logger("TaskService")

class TaskService:
    """Service to handle internal agent task tracking (State Management)."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Creates the tasks.json file if it doesn't exist."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({"tasks": []}, f, indent=2)

    def _read_data(self) -> Dict[str, Any]:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_data(self, data: Dict[str, Any]):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def create_plan(self, title: str, execution_plan: List[Dict[str, Any]], 
                    problem_analysis: Optional[Dict] = None, 
                    best_practices: Optional[List[str]] = None, 
                    risk_assessment: Optional[List[str]] = None) -> str:
        """Create a new advanced task plan containing problem analysis and detailed steps."""
        data = self._read_data()
        
        task_id = str(uuid.uuid4())[:8]
        new_task = {
            "id": task_id,
            "title": title,
            "created_at": str(datetime.now()),
            "status": "in_progress",
            "problem_analysis": problem_analysis or {},
            "best_practices": best_practices or [],
            "risk_assessment": risk_assessment or [],
            "steps": []
        }
        
        for i, step_data in enumerate(execution_plan):
            new_task["steps"].append({
                "index": step_data.get("step", i + 1),
                "action": step_data.get("action", ""),
                "expected_result": step_data.get("expected_result", ""),
                "status": "todo"
            })
            
        data["tasks"].append(new_task)
        self._write_data(data)
        logger.info(f"Created advanced task plan: {title} ({task_id})")
        return task_id

    def mark_step(self, task_id: str, step_index: int, status: str) -> str:
        """Update the status of a specific step (todo, in_progress, done)."""
        if status not in ["todo", "in_progress", "done"]:
            return "Error: Status must be 'todo', 'in_progress', or 'done'."

        data = self._read_data()
        for task in data["tasks"]:
            if task["id"] == task_id:
                for step in task["steps"]:
                    if step["index"] == step_index:
                        step["status"] = status
                        
                        # Eğer tüm stepler done ise, taskı done yap
                        if all(s["status"] == "done" for s in task["steps"]):
                            task["status"] = "done"
                        elif any(s["status"] == "in_progress" for s in task["steps"]):
                            task["status"] = "in_progress"
                        
                        self._write_data(data)
                        return f"Success: Marked task {task_id} step {step_index} as {status}."
                return f"Error: Step {step_index} not found in task {task_id}."
        
        return f"Error: Task {task_id} not found."

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Retrieve all non-completed tasks."""
        data = self._read_data()
        active_tasks = [task for task in data["tasks"] if task["status"] != "done"]
        return active_tasks

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Retrieve all recorded tasks across time."""
        return self._read_data().get("tasks", [])
