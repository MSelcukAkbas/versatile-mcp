from typing import List, Dict, Optional, Any
from datetime import datetime
from services.core.logger_service import setup_logger
from services.ai.orchestration_engine import OrchestrationEngine

logger = setup_logger("ThinkingService")

class ThinkingService:
    """
    Full-featured sequential thinking session manager.
    Supports linear chains, revisions, and branching.
    Removed AuditService dependency: Uses in-memory history for loop detection.
    """

    def __init__(self, memory_svc=None, file_svc=None):
        self.history: List[Dict[str, Any]] = []
        self.branches: Dict[str, List[Dict[str, Any]]] = {}
        self.memory_svc = memory_svc
        self.file_svc = file_svc
        self.orchestration = OrchestrationEngine()

    # ------------------------------------------------------------------ #
    #  Core                                                                #
    # ------------------------------------------------------------------ #

    async def add_thought(
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
        context: Optional[Dict[str, Any]] = None,
        memory_keys: Optional[List[str]] = None,
        available_tools: Optional[List[str]] = None,
        project_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a thought step, analyze it via Orchestration, inject hybrid memory, and return response."""

        # 1. Base response & entry structure
        response = {
            "thoughtNumber": thought_number,
            "totalThoughts": total_thoughts,
            "status": "revision" if is_revision else ("branch" if branch_id else "recorded"),
            "nextThoughtNeeded": next_thought_needed,
            "memory_context": []
        }

        # 2. Hybrid Memory Retrieval (Semantic + Keyword)
        if self.memory_svc and project_root:
            try:
                facts_result = []
                # Hybrid strategy: search targets are explicit keys OR the thought itself
                search_targets = memory_keys if memory_keys else [thought[:160]]
                
                for target in search_targets:
                    # A. Hybrid Search (Knowledge/Code/Context)
                    hits = await self.memory_svc.search_hybrid(target, project_root, n_results=3, file_svc=self.file_svc)
                    for hit in hits:
                        source_tag = "[K]" if "Keyword" in hit.get("source", "") else "[V]"
                        facts_result.append(f"Auto-Context {source_tag}: {hit['content'][:200]}... (File: {hit['file']})")
                    
                    # B. Keyword Search (Facts - prioritized when keys are explicit)
                    if memory_keys:
                        facts = self.memory_svc.retrieve_facts(project_root=project_root, query=target, scope="all")
                        for f in facts:
                            facts_result.append(f"Fact: {f['fact']} (Scope: {f['scope']})")
                
                response["memory_context"] = list(dict.fromkeys(facts_result))
            except Exception as e:
                logger.error(f"Hybrid memory retrieval failed: {e}")

        # 3. Analyze through Advanced Orchestration Engine (Using in-memory history)
        # Extract last few tool suggestions to detect loops
        recent_actions = []
        target_history = self.branches.get(branch_id) if branch_id else self.history
        if target_history:
            recent_actions = [h.get("suggested_tool") for h in target_history[-3:] if h.get("suggested_tool")]

        analysis = self.orchestration.analyze(
            thought=thought, 
            context=context or {}, 
            available_tools=available_tools or [],
            memory_context=response["memory_context"],
            recent_actions=recent_actions
        )
        
        # Merge analysis directly into response
        response.update(analysis)

        # 4. Record entry into history (including the analysis result for future loop detection)
        entry = {
            "thoughtNumber": thought_number,
            "totalThoughts": total_thoughts,
            "thought": thought,
            "timestamp": datetime.now().isoformat(),
            "suggested_tool": response.get("tool_suggestion", {}).get("tool")
        }
        
        if branch_id:
            if branch_id not in self.branches:
                self.branches[branch_id] = []
            self.branches[branch_id].append(entry)
            logger.info(f"[Branch:{branch_id}] Thought {thought_number}/{total_thoughts}: {thought[:80]}...")
        else:
            self.history.append(entry)
            logger.info(f"[Thought {thought_number}/{total_thoughts}]{'[REVISION]' if is_revision else ''} {thought[:80]}...")

        return response

    # ------------------------------------------------------------------ #
    #  Session Management                                                  #
    # ------------------------------------------------------------------ #

    def clear_history(self):
        """Reset the thinking history for a fresh session."""
        self.history = []
        self.branches = {}
        logger.info("Thinking history cleared.")

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the current linear history."""
        return self.history
