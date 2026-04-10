from .ai_assistant import register_ai_tools
from .reasoning import register_reasoning_tools
from .research import register_research_tools
from .file_ops import register_file_tools
from .memory import register_memory_tools
from .task_management import register_task_tools
from .diagnostics import register_diagnostic_tools

def register_all_tools(mcp, services, paths, ollama_ready: bool):
    # Specialized Intelligence tools
    if ollama_ready:
        register_ai_tools(mcp, services['ollama'], services['prompt'])
    else:
        services['logger'].warning("Ollama is not ready. AI Assistant tools will not be registered.")
    register_reasoning_tools(mcp, services['thinking'])
    register_research_tools(mcp, services['search'], services['validator'], services['stackoverflow'])
    
    # Other domains
    register_file_tools(mcp, services['file'])
    register_memory_tools(
        mcp, 
        services['memory'], 
        services['task'], 
        paths['PROJECT_ROOT'], 
        services['logger']
    )
    register_task_tools(mcp, services['task'], services['planner'])
    register_diagnostic_tools(
        mcp, 
        paths['audit_logs'], 
        paths['memory'], 
        paths['PROJECT_ROOT'], 
        paths['SERVER_HOME']
    )
