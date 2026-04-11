import json
from typing import List, Dict, Optional, Any
from services.core.logger_service import setup_logger

logger = setup_logger("ThinkingService")


class ThinkingService:
    """
    Full-featured sequential thinking session manager.
    Supports linear chains, revisions, and branching.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.branches: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------ #
    #  Core                                                                #
    # ------------------------------------------------------------------ #

    def add_thought(
        self,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool = True,
        is_revision: bool = False,
        revises_thought: Optional[int] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        needs_more_thoughts: bool = False,
    ) -> Dict[str, Any]:
        """Add a thought step and return a structured status object."""

        entry = {
            "thoughtNumber": thought_number,
            "totalThoughts": total_thoughts,
            "thought": thought,
            "nextThoughtNeeded": next_thought_needed,
            "isRevision": is_revision,
            "revisesThought": revises_thought,
            "branchFromThought": branch_from_thought,
            "branchId": branch_id,
            "needsMoreThoughts": needs_more_thoughts,
        }

        # Route to branch or main history
        if branch_id:
            if branch_id not in self.branches:
                self.branches[branch_id] = []
            self.branches[branch_id].append(entry)
            logger.info(f"[Branch:{branch_id}] Thought {thought_number}/{total_thoughts}: {thought[:80]}...")
        else:
            self.history.append(entry)
            logger.info(f"[Thought {thought_number}/{total_thoughts}]{'[REVISION]' if is_revision else ''} {thought[:80]}...")

        return {
            "thoughtNumber": thought_number,
            "totalThoughts": total_thoughts,
            "nextThoughtNeeded": next_thought_needed,
            "branches": list(self.branches.keys()),
            "thoughtHistoryLength": len(self.history),
            "status": "revision" if is_revision else ("branch" if branch_id else "recorded"),
        }

    # ------------------------------------------------------------------ #
    #  Session Management                                                  #
    # ------------------------------------------------------------------ #

    def get_history(self) -> Dict[str, Any]:
        """Return the full current session state."""
        return {
            "history": self.history,
            "branches": self.branches,
            "totalThoughts": len(self.history),
            "totalBranches": len(self.branches),
        }

    def clear_history(self):
        """Reset the entire session including branches."""
        self.history = []
        self.branches = {}
        logger.info("Thinking session cleared.")
