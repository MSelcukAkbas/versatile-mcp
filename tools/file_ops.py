import json
import os
import re
from typing import Optional, List
from fastmcp import FastMCP

def register_file_tools(mcp: FastMCP, file_svc, diag_svc):
    @mcp.tool()
    async def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Read a file with optional line range."""
        try: return file_svc.read_file(file_path, start_line, end_line)
        except Exception as e: return str(e)

    @mcp.tool()
    async def read_text_file(file_path: str) -> str:
        """Read a full text file."""
        try: return file_svc.read_text_file(file_path)
        except Exception as e: return str(e)

    @mcp.tool()
    async def read_media_file(file_path: str) -> str:
        """Get metadata for media files (images, audio, etc.)."""
        try: return json.dumps(file_svc.read_media_file(file_path), indent=2)
        except Exception as e: return str(e)

    @mcp.tool()
    async def read_multiple_files(file_paths: List[str]) -> str:
        """Read multiple files at once."""
        try:
            res = file_svc.read_multiple(file_paths)
            return "\n".join([f"--- {p} ---\n{c}" for p, c in res.items()])
        except Exception as e: return str(e)

    @mcp.tool()
    async def write_file(file_path: str, content: str) -> str:
        """Write or overwrite a file."""
        try: return file_svc.write_file(file_path, content)
        except Exception as e: return str(e)

    @mcp.tool()
    async def edit_file(file_path: str, target_content: str, replacement_content: str) -> str:
        """Search and replace content in a file."""
        try: return file_svc.edit_file(file_path, target_content, replacement_content)
        except Exception as e: return str(e)

    @mcp.tool()
    async def create_directory(directory: str) -> str:
        """Create a new directory."""
        try: return file_svc.create_directory(directory)
        except Exception as e: return str(e)

    @mcp.tool()
    async def list_directory(directory: str = ".") -> str:
        """List directory contents."""
        try: return "Contents: " + ", ".join(file_svc.list_directory(directory))
        except Exception as e: return str(e)

    @mcp.tool()
    async def list_directory_with_sizes(directory: str = ".") -> str:
        """List directory contents with file sizes."""
        try: return json.dumps(file_svc.list_directory_with_sizes(directory), indent=2)
        except Exception as e: return str(e)

    @mcp.tool()
    async def directory_tree(directory: str = ".", max_depth: int = 3) -> str:
        """Show visual directory structure."""
        try: return file_svc.directory_tree(directory, max_depth)
        except Exception as e: return str(e)

    @mcp.tool()
    async def move_file(source_path: str, dest_path: str) -> str:
        """Move or rename a file/directory."""
        try: return file_svc.move_file(source_path, dest_path)
        except Exception as e: return str(e)

    @mcp.tool()
    async def search_files(pattern: str, directory: str = ".") -> str:
        """Search for files matching a pattern."""
        err = await diag_svc.check_tool_dependency("search_files")
        if err: return err
        try:
            matches = file_svc.search_files(pattern, directory)
            return "Matches: " + ", ".join(matches) if matches else "No matches found."
        except Exception as e: return str(e)

    @mcp.tool()
    async def search_content(query: str, directory: str = ".") -> str:
        """
        Search for text within files using Ripgrep (rg). 
        Extremely fast text search within files.
        """
        err = await diag_svc.check_tool_dependency("search_content")
        if err: return err
        try:
            results = file_svc.search_content(query, directory)
            return json.dumps(results, indent=2)
        except Exception as e: return str(e)

    @mcp.tool()
    async def get_file_info(file_path: str) -> str:
        """Get detailed metadata for a file."""
        try: return json.dumps(file_svc.get_file_info(file_path), indent=2)
        except Exception as e: return str(e)

    @mcp.tool()
    async def list_allowed_directories() -> str:
        """List allowed project directories."""
        return f"Allowed: {file_svc.list_allowed_directories()}"

    # --- Feature: Diff & Patch ---

    @mcp.tool()
    async def diff_files(path_a: str, path_b: str, context_lines: int = 3) -> str:
        """Return a unified diff between two files."""
        try:
            return file_svc.diff_files(path_a, path_b, context_lines)
        except Exception as e:
            return str(e)

    @mcp.tool()
    async def diff_strings(text_a: str, text_b: str,
                           label_a: str = "original", label_b: str = "modified",
                           context_lines: int = 3) -> str:
        """Return a unified diff between two text strings."""
        try:
            return file_svc.diff_strings(text_a, text_b, label_a, label_b, context_lines)
        except Exception as e:
            return str(e)

    @mcp.tool()
    async def apply_patch(target_path: str, patch_text: str) -> str:
        """Apply a unified diff patch to a file in-place."""
        try:
            return file_svc.apply_patch(target_path, patch_text)
        except Exception as e:
            return str(e)

    # --- Feature: Env File Manager ---

    _SENSITIVE = re.compile(r"(secret|token|password|passwd|key|api_key|auth)", re.IGNORECASE)

    @mcp.tool()
    async def read_env_file(env_path: str) -> str:
        """
        Parse a .env file and return its key-value pairs.
        Values whose keys match sensitive patterns (SECRET, TOKEN, PASSWORD, KEY…) are masked.
        """
        try:
            raw = file_svc.read_text_file(env_path)
        except Exception as e:
            return str(e)

        rows = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if _SENSITIVE.search(key):
                val = "***"
            rows.append(f"{key}={val}")
        return "\n".join(rows) if rows else "(empty .env file)"

    @mcp.tool()
    async def write_env_key(env_path: str, key: str, value: str) -> str:
        """Add or update a key in a .env file."""
        try:
            try:
                raw = file_svc.read_text_file(env_path)
            except FileNotFoundError:
                raw = ""

            lines = raw.splitlines(keepends=True)
            found = False
            new_lines = []
            for line in lines:
                if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                    new_lines.append(f"{key}={value}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines.append("\n")
                new_lines.append(f"{key}={value}\n")

            file_svc.write_file(env_path, "".join(new_lines))
            action = "updated" if found else "added"
            return f"Key '{key}' {action} in {env_path}."
        except Exception as e:
            return str(e)
