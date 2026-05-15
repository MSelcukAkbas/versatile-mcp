import json
from typing import Optional
from fastmcp import FastMCP

def register_reasoning_tools(mcp: FastMCP, thinking_loop, validate_project_root):
    
    @mcp.tool()
    async def sequentialthinking(
        thought: str,
        thought_number: int,
        total_thoughts: int,
        next_thought_needed: bool,
        project_root: str,
        context: Optional[dict] = None,
        session_id: str = "default",
    ) -> str:
        """
        An advanced reasoning framework for tackling complex, multi-step engineering problems.
        This tool implements a structured thinking process that helps avoid cognitive loops, 
        detects contradictions in logic, and maintains state across deep technical analyses.
        
        Use this tool when you need to plan a large refactor, debug a race condition, or 
        design a new system component. It records each thought step in the project's reasoning history.
        
        IMPORTANT: 'project_root' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') to correctly 
        link the reasoning session to the project's permanent memory.
        
        Args:
            thought: The actual content of your current reasoning step. Be specific and analytical.
            thought_number: The current index of this thought in the sequence (1, 2, 3...).
            total_thoughts: Your current estimation of how many steps this analysis will take.
            next_thought_needed: Set to True if you need more steps, False if you have reached a conclusion.
            project_root: The full ABSOLUTE path to the project root. DO NOT use relative paths.
            context: Optional technical data or tool outputs to include as evidence for this thought.
            session_id: A unique identifier to group related thoughts (defaults to "default").
        """
        project_root = validate_project_root(project_root)
        result = await thinking_loop.add_thought(
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            context=context,
            project_root=project_root,
            session_id=session_id,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
