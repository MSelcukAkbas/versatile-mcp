from typing import List, Dict, Any, Optional
from .security import SecurityManager
from .io_manager import IOManager
from .reader import SmartReader
from .patcher import Patcher
from .search_engine import SearchEngine
from .inspector import CodeInspector

class FileSystemService:
    """Consolidated service for filesystem operations using modular components."""
    
    def __init__(self, allowed_roots: List[str], ignore_svc: Optional[Any] = None,
                 bin_service: Optional[Any] = None, doc_svc: Optional[Any] = None):
        self.security = SecurityManager(allowed_roots)
        self.io = IOManager()
        self.reader = SmartReader(doc_svc)
        self.patcher = Patcher()
        self.ignore_svc = ignore_svc

        from servers.master.services.analysis.explorer import Explorer
        self.explorer = Explorer(str(self.security.allowed_roots[0]), ignore_svc)

        if bin_service:
            self.searcher = SearchEngine(bin_service, str(self.security.allowed_roots[0]))
        else:
            self.searcher = None

    def read_file(self, file_path: str, start_line: Optional[int] = None, 
                  end_line: Optional[int] = None, mode: str = "auto", doc_svc: Optional[Any] = None) -> str:
        resolved = self.security.resolve_path(file_path)
        reader = self.reader
        if doc_svc:
            from .reader import SmartReader
            reader = SmartReader(doc_svc)
        return reader.read(resolved, mode, start_line, end_line)

    def read_multiple(self, file_paths: List[str]) -> Dict[str, str]:
        results = {}
        for path in file_paths:
            try:
                results[path] = self.read_file(path)
            except Exception as e:
                results[path] = f"Error: {str(e)}"
        return results

    async def search_content(self, query: str, directory: str = ".", includes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Searches for text content across files using the underlying search engine."""
        if not self.searcher:
            return [{"error": "Search engine (ripgrep) not initialized."}]
        return await self.searcher.search_content(query, directory, includes)

    def directory_tree(self, directory: str = ".", max_depth: int = 3) -> str:
        return self.explorer.get_tree(directory, max_depth)
