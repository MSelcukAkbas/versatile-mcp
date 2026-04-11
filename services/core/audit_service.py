import os
import json
import time
from datetime import datetime, timezone
from typing import Any
from fastmcp.server.middleware import Middleware, MiddlewareContext
from services.core.logger_service import setup_logger

logger = setup_logger("AuditService")

# Max characters to store per input/output field.
# Prevents huge outputs (e.g. workspace indexing) from bloating log files.
MAX_FIELD_CHARS = 32_000


def _safe_serialize(value: Any, label: str = "value") -> str:
    """
    Safely convert any value to a UTF-8 safe string.
    Truncates if over MAX_FIELD_CHARS.
    Never raises.
    """
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        try:
            text = str(value)
        except Exception:
            return f"[{label}: UNSERIALIZABLE]"

    if len(text) > MAX_FIELD_CHARS:
        truncated_len = len(text)
        text = text[:MAX_FIELD_CHARS] + f" ... [TRUNCATED — original {truncated_len} chars]"

    return text


class AuditService:
    """
    Writes all tool call records to hourly JSON Lines (.jsonl) files.

    JSON Lines = one JSON object per line.
    Each line is self-contained → even partial files are parseable.
    Encoding-safe: json.dumps handles any Unicode correctly.
    """

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        logger.info(f"AuditService initialized. Log dir: {self.log_dir}")

    def _get_log_path(self) -> str:
        """Return the path for the current hour's .jsonl file."""
        now = datetime.now()
        filename = f"audit_{now.strftime('%Y%m%d_%H')}.jsonl"
        return os.path.join(self.log_dir, filename)

    def log_call(
        self,
        tool_name: str,
        arguments: Any,
        result: Any,
        duration: float,
        status: str = "ok",
        error: str = None
    ):
        """Append one audit record as a JSON line."""
        try:
            # Extract project_root from arguments if present
            project_root = None
            if isinstance(arguments, dict):
                project_root = arguments.get("project_root")

            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
                "input": _safe_serialize(arguments, label="input"),
                "output": _safe_serialize(result, label="output"),
            }
            if project_root:
                record["project_root"] = project_root
            if error:
                record["error"] = error[:2000]  # cap error messages too

            line = json.dumps(record, ensure_ascii=False) + "\n"

            filepath = self._get_log_path()
            if not os.path.exists(self.log_dir):
                try:
                    os.makedirs(self.log_dir, exist_ok=True)
                except:
                    pass # Silently fail if we can't create dir, avoid crashing the app
                
            try:
                with open(filepath, "a", encoding="utf-8", errors="replace") as f:
                    f.write(line)
            except Exception as e:
                # We don't use the regular logger here to avoid recursion if logger uses audit
                print(f"AuditService failed to write log entry: {e}")

        except Exception as e:
            # Logging must NEVER crash the server — silent fallback
            logger.error(f"AuditService failed to write log entry: {e}")


class AuditMiddleware(Middleware):
    """FastMCP Middleware to intercept every tool call for auditing."""

    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = getattr(context.message, "name", "unknown")
        arguments = getattr(context.message, "arguments", {})

        logger.debug(f"→ TOOL CALL : {tool_name} | args={_safe_serialize(arguments)[:300]}")
        start_time = time.perf_counter()

        try:
            result = await call_next(context)
            duration = time.perf_counter() - start_time
            logger.debug(f"← TOOL DONE : {tool_name} | {duration*1000:.1f}ms | OK")
            self.audit_service.log_call(tool_name, arguments, result, duration, status="ok")
            return result

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(f"← TOOL ERROR: {tool_name} | {duration*1000:.1f}ms | {e}")
            self.audit_service.log_call(
                tool_name, arguments, None, duration,
                status="error", error=str(e)
            )
            raise
