"""
MCP Tools — Reasoning (4 tool)

sequentialthinking_add_thought : Düşünce zinciri adımı
reasoning_trace_write          : Manuel trace yazma
reasoning_trace_query          : Trace'lerde semantik arama
reasoning_distill              : Reasoning → Memory terfi
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from core.envelope import validate_request, make_success, make_error, format_graph_hints, EnvelopeError
from ..services.reasoning_service import ReasoningService
from ..services.distillation_service import DistillationService

logger = logging.getLogger("ReasoningTools")


def register_reasoning_tools(
    mcp: FastMCP,
    reasoning_svc: ReasoningService,
    distillation_svc: DistillationService,
) -> None:

    @mcp.tool()
    def sequentialthinking_add_thought(
        project_root: str,
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        session_id: str = None,
        context: dict = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool as your PRIMARY METHOD for complex problem-solving, architectural design, debugging, or analyzing ambiguous requirements.
        This is a Sequential Thinking framework that records your thought process, detects loops/contradictions, and automatically cross-references your thoughts with long-term memory.

        HOW IT WORKS:
        1. You submit a 'thought'.
        2. The system checks if you are repeating yourself (Loop Detection) or contradicting established facts (Contradiction Detection).
        3. The system scans the permanent memory (Cross-Feed) for related context and returns it.
        4. It scores your progress and provides a recommendation on what to do next.

        RULES & CONSTRAINTS:
        - `thought` should be a substantial, focused piece of reasoning (not just a single sentence).
        - Plan how many thoughts you need (`total_thoughts`) and increment `thought_number`.
        - If `next_thought_needed=False`, it marks the session as concluded.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            thought: Your detailed reasoning, analysis, or hypothesis.
            thought_number: Current step number in your thought process (1-based).
            total_thoughts: Estimated total number of steps to reach a conclusion.
            next_thought_needed: True if you plan to continue thinking after this, False if concluding.
            session_id: The ID of the current reasoning session. Leave None to start a new session.
            context: Optional JSON dict with contextual data (e.g., error logs, current file path).
        """
        try:
            normalized_root = validate_request(project_root, "reasoning")
        except EnvelopeError as e:
            return make_error(str(e))

        result = reasoning_svc.add_thought(
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            project_root=normalized_root,
            session_id=session_id,
            context=context,
        )

        return make_success(
            data=result,
            namespace="reasoning",
            project_root=normalized_root,
            confidence=result.get("intelligence", {}).get("progress_score", 0.0),
            node_id=result.get("trace_id"),
        )

    @mcp.tool()
    def reasoning_trace_write(
        project_root: str,
        thought: str,
        data_class: str = "inference",
        session_id: str = None,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to manually write a specific thought, inference, or hypothesis directly into the reasoning database WITHOUT using the full sequential thinking pipeline.
        
        HOW IT WORKS:
        - Stores a single reasoning trace under a session.

        RULES & CONSTRAINTS:
        - Generally, prefer `sequentialthinking_add_thought` for problem solving. Use this only for isolated manual logging.
        - `data_class` must be one of: inference, decision, hypothesis, speculation.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            thought: The thought or hypothesis text.
            data_class: Must be 'inference', 'decision', 'hypothesis', or 'speculation'.
            session_id: Optional session ID to attach this trace to.
        """
        try:
            normalized_root = validate_request(project_root, "reasoning")
        except EnvelopeError as e:
            return make_error(str(e))

        trace_id = reasoning_svc.trace_write(
            thought=thought,
            project_root=normalized_root,
            data_class=data_class,
            session_id=session_id,
        )

        return make_success(
            data={"trace_id": trace_id},
            namespace="reasoning",
            project_root=normalized_root,
            node_id=trace_id,
        )

    @mcp.tool()
    def reasoning_trace_query(
        project_root: str,
        query: str,
        n: int = 5,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool to search exclusively through your past reasoning traces, thoughts, and hypotheses.
        DO NOT use this to find factual ground truth memory (use `memory_query` for that).

        HOW IT WORKS:
        - Performs a semantic vector search restricted to the 'reasoning' namespace.

        RULES & CONSTRAINTS:
        - Useful to recall how you solved a similar problem in the past before the conclusion was distilled.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            query: The semantic search query to find past thoughts.
            n: Maximum number of traces to return (default 5).
        """
        try:
            normalized_root = validate_request(project_root, "reasoning")
        except EnvelopeError as e:
            return make_error(str(e))

        results = reasoning_svc.trace_query(
            query=query,
            project_root=normalized_root,
            n=n,
        )

        return make_success(
            data={"results": results, "count": len(results)},
            namespace="reasoning",
            project_root=normalized_root,
        )

    @mcp.tool()
    def reasoning_distill(
        project_root: str,
        session_id: str = None,
        trace_id: str = None,
        target_namespace: str = "project",
        confidence: float = 0.8,
    ) -> dict:
        """
        CRITICAL AGENT INSTRUCTION:
        Use this tool ONLY AFTER you have reached a firm, verified conclusion in a reasoning session and want to promote that conclusion into permanent Ground Truth memory.
        This is how your thoughts become permanent system facts (Cross-Feed: Reasoning -> Memory).

        HOW IT WORKS:
        - Takes the 'conclusions' of a reasoning session (or a specific trace).
        - Compiles them and inserts them into the standard memory graph (usually in the 'project' namespace).
        - Creates explicit traceability links between the permanent memory node and your reasoning traces.

        RULES & CONSTRAINTS:
        - `confidence` MUST be 0.85 or higher. If you are not highly confident, DO NOT distill.
        - You must provide either a `session_id` (to distill the whole session's conclusions) or a `trace_id`.

        Args:
            project_root: The absolute path of the current project (Mandatory).
            session_id: ID of the completed reasoning session to distill.
            trace_id: ID of a specific trace to distill (if not distilling a full session).
            target_namespace: Where to store the permanent memory (default 'project').
            confidence: Float between 0.85 and 1.0 representing absolute certainty in the conclusion.
        """
        try:
            normalized_root = validate_request(project_root, target_namespace)
        except EnvelopeError as e:
            return make_error(str(e))

        if confidence < 0.85:
            return make_error(
                "Güvenlik Kuralı İhlali: Ground truth memory'ye bilgi aktarmak (distill) için "
                f"confidence en az 0.85 olmalıdır. Verilen: {confidence}",
                target_namespace, normalized_root
            )

        if session_id:
            result = distillation_svc.distill_session(
                session_id=session_id,
                project_root=normalized_root,
                target_namespace=target_namespace,
                confidence=confidence,
            )
        elif trace_id:
            result = distillation_svc.distill_trace(
                trace_id=trace_id,
                project_root=normalized_root,
                target_namespace=target_namespace,
                confidence=confidence,
            )
        else:
            return make_error(
                "session_id veya trace_id verilmeli.",
                target_namespace, normalized_root,
            )

        if "error" in result:
            return make_error(result["error"], target_namespace, normalized_root)

        return make_success(
            data=result,
            namespace=target_namespace,
            project_root=normalized_root,
            confidence=confidence,
            node_id=result.get("distilled_node_id"),
        )
