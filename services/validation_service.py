import json
import yaml
import ast
import subprocess
import tempfile
import os
import xml.etree.ElementTree as ET
from services.logger_service import setup_logger
from services.bin_service import BinService
from config.settings import PATHS
from typing import Tuple
from pathlib import Path

logger = setup_logger("ValidationService")

class ValidationService:
    """Service to validate syntax of various file formats using high-performance tools."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.bin_service = BinService(self.project_root)
        logger.info("ValidationService initialized with BinService.")

    def _run_tool(self, tool_name: str, args: list) -> Tuple[int, str, str]:
        """Generic helper to run a tool via BinService."""
        tool_path = self.bin_service.get_binary_path(tool_name)
        if not tool_path:
            return -1, "", f"Tool {tool_name} not found in bin/ or PATH."
            
        cmd = [str(tool_path)] + args
        try:
            # Use shell=True on Windows for consistency with previous implementation
            is_win = os.name == 'nt'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=is_win)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            logger.error(f"Error running {tool_name}: {e}")
            return -1, "", str(e)

    def _validate_js_ts(self, content: str, ext: str) -> Tuple[bool, str]:
        """Validate JS/TS using Oxlint (primary) or Biome (fallback)."""
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False, mode='w', encoding='utf-8') as tf:
            tf.write(content)
            temp_path = tf.name

        try:
            # Try Oxlint first
            rc, stdout, stderr = self._run_tool("oxlint", ["-D", "correctness", "--format", "json", temp_path])
            
            if rc != -1 and stdout:
                try:
                    data = json.loads(stdout)
                    diagnostics = data.get("diagnostics", [])
                    if not diagnostics:
                        return True, "SYNTAX OK (Oxlint)"
                    
                    err = diagnostics[0]
                    msg = f"[Oxlint: {err.get('code')}] {err.get('message')}"
                    return False, msg
                except:
                    pass

            # Fallback to Biome if available
            rc, stdout, stderr = self._run_tool("biome", ["lint", "--format", "json", temp_path])
            if rc != -1:
                # Biome parsing logic would go here
                if rc == 0:
                    return True, "SYNTAX OK (Biome)"
                return False, f"Biome detected errors. {stderr[:100]}"

            return False, "Validation tools (oxlint/biome) failed or not found."
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _validate_python_ruff(self, content: str) -> Tuple[bool, str]:
        """Validate Python using Ruff (beyond simple ast.parse)."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w', encoding='utf-8') as tf:
            tf.write(content)
            temp_path = tf.name

        try:
            # ruff check --output-format json --cache-dir <central_path> <path>
            cache_dir = os.path.join(PATHS["GLOBAL_DATA"], "cache", "ruff")
            rc, stdout, stderr = self._run_tool("ruff", [
                "check", 
                "--output-format", "json", 
                "--cache-dir", cache_dir,
                temp_path
            ])
            
            if rc == -1:
                # If ruff not found, fallback to standard ast.parse
                ast.parse(content)
                return True, "SYNTAX OK (AST fallback)"

            if rc == 0:
                return True, "SYNTAX OK (Ruff)"
                
            try:
                data = json.loads(stdout)
                if not data:
                    return True, "SYNTAX OK (Ruff empty)"
                
                err = data[0]
                msg = f"[Ruff: {err.get('code')}] {err.get('message')} at line {err.get('location', {}).get('row')}"
                return False, msg
            except Exception as pe:
                return False, f"Ruff found errors but output parse failed: {str(pe)}"

        except Exception as e:
            return False, str(e)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def validate(self, content: str, ext: str) -> Tuple[bool, str]:
        """
        Validate content based on extension.
        Returns (is_valid, message).
        """
        ext = ext.lower().strip('.')
        logger.info(f"validate() | ext=.{ext} | content_length={len(content)} chars")

        try:
            if ext == "json":
                json.loads(content)
            elif ext in ["yaml", "yml"]:
                yaml.safe_load(content)
            elif ext == "py":
                return self._validate_python_ruff(content)
            elif ext == "xml":
                ET.fromstring(content)
            elif ext in ["js", "mjs", "cjs", "ts", "mts", "cts"]:
                return self._validate_js_ts(content, ext)
            else:
                logger.warning(f"validate() | Unsupported extension: .{ext}")
                return False, f"Unsupported extension: {ext}"
            
            logger.info(f"validate() | PASS | ext=.{ext}")
            return True, "SYNTAX OK"

        except Exception as e:
            logger.warning(f"validate() | FAIL | ext=.{ext} | error={str(e)}")
            return False, str(e)
