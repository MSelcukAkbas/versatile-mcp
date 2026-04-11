import os
import shutil
import time
import json
import pathlib
import subprocess
from services.core.logger_service import setup_logger
from services.core.bin_service import BinService
from typing import List, Optional, Dict, Any

logger = setup_logger("FileService")

class FileService:
    """Advanced Service to handle secure file and directory operations."""
    
    def __init__(self, allowed_roots: List[str]):
        """Initialize with a list of allowed root directories."""
        self.allowed_roots = [pathlib.Path(p).resolve() for p in allowed_roots]
        self.bin_service = BinService(pathlib.Path(__file__).parent.parent)
        logger.info(f"FileService initialized with {len(self.allowed_roots)} allowed roots and BinService.")

    def _resolve_path(self, target_path: str) -> str:
        """Resolve path and verify it is within one of the allowed roots."""
        try:
            # Handle both absolute and relative paths
            p = pathlib.Path(target_path)
            
            # If relative, we assume it's relative to the first allowed root (usually PROJECT_ROOT)
            if not p.is_absolute():
                p = self.allowed_roots[0] / target_path
            
            abs_path = p.resolve()
            
            # Check if it's within ANY of the allowed roots
            # is_relative_to is case-insensitive on Windows and handles normalization
            for root in self.allowed_roots:
                if abs_path == root or abs_path.is_relative_to(root):
                    return str(abs_path)
            
            allowed_str = ", ".join([str(r) for r in self.allowed_roots])
            raise PermissionError(
                f"Access denied: '{target_path}' is outside allowed roots.\n"
                f"Allowed roots: {allowed_str}"
            )
        except Exception as e:
            if isinstance(e, PermissionError):
                raise
            raise ValueError(f"Invalid path: {target_path}. Error: {str(e)}")

    # --- Directory Operations ---
    def list_directory(self, directory: str = ".") -> List[str]:
        target_dir = self._resolve_path(directory)
        return os.listdir(target_dir)

    def list_directory_with_sizes(self, directory: str = ".") -> List[Dict[str, Any]]:
        target_dir = self._resolve_path(directory)
        items = []
        for name in os.listdir(target_dir):
            path = os.path.join(target_dir, name)
            items.append({
                "name": name,
                "is_dir": os.path.isdir(path),
                "size": os.path.getsize(path) if os.path.isfile(path) else 0
            })
        return items

    def create_directory(self, directory: str) -> str:
        target_dir = self._resolve_path(directory)
        os.makedirs(target_dir, exist_ok=True)
        return f"Directory created: {directory}"

    def directory_tree(self, directory: str = ".", max_depth: int = 3) -> str:
        """Generates a visual tree structure of the directory."""
        target_dir = self._resolve_path(directory)
        tree = []
        
        def _build_tree(cur_path, prefix="", depth=0):
            if depth > max_depth: return
            names = sorted(os.listdir(cur_path))
            for i, name in enumerate(names):
                full_path = os.path.join(cur_path, name)
                is_last = (i == len(names) - 1)
                connector = "└── " if is_last else "├── "
                tree.append(f"{prefix}{connector}{name}")
                if os.path.isdir(full_path):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    _build_tree(full_path, new_prefix, depth + 1)
        
        tree.append(os.path.basename(target_dir) or ".")
        _build_tree(target_dir)
        return "\n".join(tree)

    # --- File Operations ---
    def read_file(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        target_file = self._resolve_path(file_path)
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if start_line or end_line:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                return "".join(lines[start:end])
            return "".join(lines)

    def read_text_file(self, file_path: str) -> str:
        return self.read_file(file_path)

    def read_media_file(self, file_path: str) -> Dict[str, Any]:
        """Returns metadata for media files (LLM doesn't read raw bytes)."""
        target_file = self._resolve_path(file_path)
        stat = os.stat(target_file)
        return {
            "name": os.path.basename(file_path),
            "size_bytes": stat.st_size,
            "modified": time.ctime(stat.st_mtime),
            "extension": os.path.splitext(file_path)[1].lower(),
            "status": "Ready for client-side rendering"
        }

    def write_file(self, file_path: str, content: str) -> str:
        target_file = self._resolve_path(file_path)
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"

    def edit_file(self, file_path: str, target_content: str, replacement_content: str) -> str:
        """Simple find and replace in a file."""
        target_file = self._resolve_path(file_path)
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if target_content not in content:
            return "Error: Target content not found in file."
        
        new_content = content.replace(target_content, replacement_content)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"Successfully edited {file_path}"

    def move_file(self, source_path: str, dest_path: str) -> str:
        src = self._resolve_path(source_path)
        dst = self._resolve_path(dest_path)
        shutil.move(src, dst)
        return f"Moved {source_path} to {dest_path}"

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        target_file = self._resolve_path(file_path)
        stat = os.stat(target_file)
        return {
            "path": file_path,
            "size": stat.st_size,
            "is_dir": os.path.isdir(target_file),
            "created": time.ctime(stat.st_ctime),
            "modified": time.ctime(stat.st_mtime)
        }

    def search_files(self, pattern: str, directory: str = ".") -> List[str]:
        """Search for files matching a pattern (case-insensitive)."""
        target_dir = self._resolve_path(directory)
        matches = []
        for root, _, files in os.walk(target_dir):
            for name in files:
                if pattern.lower() in name.lower():
                    matches.append(os.path.relpath(os.path.join(root, name), str(self.allowed_roots[0])))
        return matches

    def search_content(self, query: str, directory: str = ".") -> List[Dict[str, Any]]:
        """Search for text within files using Ripgrep (rg) if available, otherwise fallback."""
        target_dir = self._resolve_path(directory)
        rg_path = self.bin_service.get_binary_path("rg")
        
        if rg_path:
            logger.info(f"Searching content using Ripgrep: {query} in {directory}")
            # rg --json --case-sensitive/insensitive ...
            try:
                cmd = [str(rg_path), "--json", "-i", query, target_dir]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                matches = []
                for line in result.stdout.splitlines():
                    try:
                        data = json.loads(line)
                        if data.get("type") == "match":
                            payload = data.get("data")
                            matches.append({
                                "file": os.path.relpath(payload.get("path", {}).get("text"), str(self.allowed_roots[0])),
                                "line": payload.get("line_number"),
                                "content": payload.get("lines", {}).get("text", "").strip()
                            })
                    except:
                        continue
                return matches[:50] # Limit to 50 results
            except Exception as e:
                logger.error(f"Ripgrep search failed: {e}")
        
        # Fallback to manual search if rg not found or failed
        logger.info(f"Searching content using fallback (manual): {query}")
        matches = []
        # Manual search logic (limited for performance)
        return [{"message": "Ripgrep not found. Manual search not implemented for performance reasons."}]

    def list_allowed_directories(self) -> List[str]:
        return [str(r) for r in self.allowed_roots]

    def read_multiple(self, file_paths: List[str]) -> Dict[str, str]:
        """Read multiple files at once."""
        results = {}
        for path in file_paths:
            try:
                results[path] = self.read_text_file(path)
            except Exception as e:
                results[path] = f"Error: {str(e)}"
        return results
