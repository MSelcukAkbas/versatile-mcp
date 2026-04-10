from typing import Optional
from fastmcp import FastMCP

def register_reasoning_tools(mcp: FastMCP, thinking_svc):
    @mcp.tool()
    async def sequentialthinking(
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        is_revision: bool = False,
        revises_thought: Optional[int] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        needs_more_thoughts: bool = False,
    ) -> str:
        """
        A detailed tool for dynamic and reflective problem-solving through thoughts.
        This tool helps analyze problems through a flexible thinking process that can
        adapt and evolve. Each thought can build on, question, or revise previous insights.

        When to use this tool:
        - Breaking down complex problems into manageable steps.
        - Planning and design with room for revision.
        - Analysis that might need course correction.
        - Problems where the full scope might not be clear initially.

        Key features:
        - Adjust total_thoughts up or down as you progress.
        - Revise previous thoughts using is_revision + revises_thought.
        - Branch into alternative approaches using branch_from_thought + branch_id.
        - Add more thoughts even after reaching what seemed like the end.

        Parameters:
        - thought: Your current thinking step (analysis, revision, hypothesis, etc.).
        - thought_number: Current number in sequence (can exceed initial total).
        - total_thoughts: Estimated remaining thoughts needed (can be adjusted).
        - next_thought_needed: True if more thinking is needed.
        - is_revision: True if this thought revises a previous one.
        - revises_thought: Which thought number is being reconsidered.
        - branch_from_thought: Branching point thought number.
        - branch_id: Identifier for the current branch.
        - needs_more_thoughts: True if you realize more thoughts are needed at the end.

        Only set next_thought_needed to false when truly done and a satisfactory
        answer has been reached.
        """
        import json
        result = thinking_svc.add_thought(
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            is_revision=is_revision,
            revises_thought=revises_thought,
            branch_from_thought=branch_from_thought,
            branch_id=branch_id,
            needs_more_thoughts=needs_more_thoughts,
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def clear_thinking() -> str:
        """Clear the current sequential thinking session. Call when starting a new reasoning chain."""
        thinking_svc.clear_history()
        return "Thinking session cleared."
