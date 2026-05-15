import asyncio
import functools
from services.core.logger_service import setup_logger

logger = setup_logger("TimeoutDecorator")

def mcp_timeout(seconds: int = 60):
    """Enforce a timeout on async MCP tool functions."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Tool '{func.__name__}' timed out after {seconds}s.")
                return f"FAILURE: Tool timed out after {seconds} seconds."
            except Exception as e:
                logger.error(f"Error in tool '{func.__name__}': {e}")
                raise
        return wrapper
    return decorator
