from typing import Optional, List
from fastmcp import FastMCP
from servers.master.utils.decorators import mcp_timeout

def register_file_tools(mcp: FastMCP, file_svc, diag_svc, doc_svc=None):
    @mcp.tool()
    async def read_rich_document(
        file_path: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        mode: str = "auto",
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """
        Read one or multiple documents. Optimized for rich formats (PDF, DOCX, EPUB) 
        but also supports standard text files as a fallback.
        
        Use this tool for deep inspection of binary documents, manual extraction, or 
        reading large source files with line-range precision.

        IMPORTANT: All paths MUST be full ABSOLUTE paths (e.g., 'C:\\Users\\...') 
        to ensure the server can locate the files correctly.

        Args:
            file_path:   Path to a single file (e.g., "manual.pdf", "main.py").
            file_paths:  List of paths to read at once.
            mode:        'auto' (detect), 'text' (force plain), 'rich' (force extraction).
            start_line:  First line to return (1-indexed, single file only).
            end_line:    Last line to return (inclusive, single file only).
        """
        try:
            if file_paths:
                res = file_svc.read_multiple(file_paths)
                return "\n".join([f"--- {p} ---\n{c}" for p, c in res.items()])
            if file_path:
                return file_svc.read_file(file_path, start_line, end_line, mode=mode, doc_svc=doc_svc)
            return "Error: provide file_path or file_paths."
        except Exception as e:
            return f"Error reading document: {str(e)}"

    @mcp.tool()
    @mcp_timeout(seconds=30)
    async def directory_tree(directory: str = ".", max_depth: int = 3) -> str:
        """
        Generates a flattened Indexed File Graph of the project structure.
        
        Includes metadata such as file sizes, line counts, and identified roles 
        (e.g., config, test, core). Respects .gitignore rules.
        
        IMPORTANT: 'directory' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') 
        to accurately map the file system. Using relative paths like '.' will target the 
        server's startup directory, which may not be your project root.
        
        Args:
            directory: The root directory to map (ABSOLUTE path recommended).
            max_depth: Maximum directory depth to scan (default: 3).
        """
        try:
            return file_svc.directory_tree(directory, max_depth)
        except Exception as e:
            return f"Error generating directory tree: {str(e)}"

    @mcp.tool()
    async def grep_search(query: str, directory: str = ".", includes: Optional[List[str]] = None) -> str:
        """
        Use ripgrep to find exact pattern matches or text strings within all files in a directory.
        This is extremely fast and respects .gitignore by default.
        
        Use this tool when you need to:
        - Find where a specific function, class, or variable is defined or used.
        - Locate specific text or magic numbers across the entire codebase.
        - Audit the project for certain patterns (e.g., todos, hardcoded keys).
        
        IMPORTANT: 'directory' MUST be a full ABSOLUTE path (e.g., 'C:\\Users\\...') 
        for reliable resolution. Relative paths target the server's working directory.

        Args:
            query:     The text string to search for (exact match).
            directory: The subdirectory to search within (default is project root).
            includes:  Optional glob patterns to limit search (e.g., ["*.py", "*.js"]).
        """
        try:
            results = await file_svc.search_content(query, directory, includes)
            if not results:
                return f"No matches found for '{query}'."
            if "error" in results[0]:
                return f"Search error: {results[0]['error']}"
            
            output = [f"Found {len(results)} matches for '{query}':"]
            for r in results:
                output.append(f"{r['file']}:{r['line']}: {r['match']}")
            
            return "\n".join(output)
        except Exception as e:
            return f"Error during grep search: {str(e)}"
