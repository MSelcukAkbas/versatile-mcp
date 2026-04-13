from typing import List, Dict, Any, Optional

class ThinkingLoop:
    """Manages reasoning history and prevents infinite tool loops."""
    
    def __init__(self, max_history: int = 20):
        self.history = []
        self.max_history = max_history

    def record_step(self, tool: str, result_summary: str):
        self.history.append({"tool": tool, "result": result_summary})
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def detect_loop(self) -> bool:
        if len(self.history) < 3: return False
        # Simple recent repetition check
        last_three = [h["tool"] for h in self.history[-3:]]
        return len(set(last_three)) == 1
