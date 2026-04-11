from .ai_assistant import register_ai_tools
from .reasoning import register_reasoning_tools
from .research import register_research_tools
from .file_ops import register_file_tools
from .memory import register_memory_tools
from .task_management import register_task_tools
from .diagnostics import register_diagnostic_tools
from .rich_docs import register_rich_doc_tools

def register_all_tools(mcp, services, paths):
    diag_svc = services['diag']
    
    # Specialized Intelligence tools
    register_ai_tools(mcp, services['ollama'], services['prompt'], diag_svc)
    register_reasoning_tools(mcp, services['thinking'], diag_svc)
    register_research_tools(mcp, services['search'], services['validator'], services['stackoverflow'], diag_svc)
    
    # Other domains
    register_file_tools(mcp, services['file'], diag_svc)
    register_memory_tools(
        mcp, 
        services['memory'], 
        services['task'], 
        services['doc'],
        paths['PROJECT_ROOT'], 
        services['logger'],
        diag_svc
    )
    register_rich_doc_tools(mcp, services['doc'], services['logger'])
    register_task_tools(mcp, services['task'], services['planner'], diag_svc)
    register_diagnostic_tools(
        mcp, 
        services['diag'],
        paths['audit_logs'], 
        paths['memory'], 
        paths['PROJECT_ROOT'], 
        paths['SERVER_HOME']
    )
