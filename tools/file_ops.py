import json
import os
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
