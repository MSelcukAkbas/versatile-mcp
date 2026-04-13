from typing import List, Dict, Any, Optional
import pathlib
from .scanner import MetadataScanner
from .graph import DependencyGrapher
from .metrics import ImpactEvaluator
from .architect import Architect
from .explorer import Explorer

class WorkspaceAnalyzerService:
    """Consolidated service for workspace analysis using modular components."""
    
    def __init__(self, project_root: str, ignore_svc: Optional[Any] = None):
        self.project_root = pathlib.Path(project_root).resolve()
        self.scanner = MetadataScanner(self.project_root, ignore_svc)
        self.grapher = DependencyGrapher(self.project_root)
        self.explorer = Explorer(str(self.project_root), ignore_svc)
        self.architect = Architect()

    def analyze(self, mode: str = "fast", max_depth: int = 5) -> Dict[str, Any]:
        # 1. Scan
        files_data = self.scanner.scan(max_depth)
        
        summary = {
            "project_root": str(self.project_root),
            "stats": {"files": len(files_data), "directories": 0},
            "mode": mode,
            "architecture": self.architect.guess_architecture(files_data)
        }

        if mode == "deep":
            graph_data = self.grapher.build(files_data)
            hotspots = ImpactEvaluator.calculate_hotspots(files_data, graph_data["edges"])
            health = ImpactEvaluator.get_health_metrics(len(files_data), len(graph_data["edges"]))
            
            return {
                "summary": summary,
                "hotspots": hotspots[:10],
                "health": health,
                "signals": {"circular_dependencies": graph_data["cycles"]}
            }
        
        return {
            "summary": summary,
            "structure_preview": list(set([f['path'].split('/')[0] for f in files_data if '/' in f['path']]))
        }

    def directory_tree(self, directory: str = ".", max_depth: int = 3) -> str:
        return self.explorer.get_tree(directory, max_depth)
