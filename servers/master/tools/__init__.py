from .research import register_research_tools
from .file_ops import register_file_tools
from .diagnostics import register_diagnostic_tools


def register_all_tools(mcp, services, paths):
    diag_svc = services['diag']

    register_research_tools(mcp, services['validator'], diag_svc)
    register_file_tools(mcp, services['file'], diag_svc, services.get('doc'))

    register_diagnostic_tools(
        mcp,
        services['diag'],
        paths['audit_logs'],
        paths['memory'],
        paths['PROJECT_ROOT'],
        paths['SERVER_HOME'],
    )
