import pathlib
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from resources.config.settings import get_project_entry, save_to_registry, get_project_id, PROJECT_ID
from .scanner import MetadataScanner
from .graph import DependencyGrapher
from .metrics import ImpactEvaluator
from .architect import Architect
from .explorer import Explorer

class WorkspaceAnalyzerService:
    """Consolidated service for workspace analysis using modular components."""
    
    def __init__(self, project_root: str, ignore_svc: Optional[Any] = None):
        self.project_root = pathlib.Path(project_root).resolve()
        self.ignore_svc = ignore_svc
        self.scanner = MetadataScanner(self.project_root, ignore_svc)
        self.grapher = DependencyGrapher(self.project_root)
        self.explorer = Explorer(str(self.project_root), ignore_svc)
        self.architect = Architect()

    def analyze(self, mode: str = "fast", max_depth: int = 5) -> Dict[str, Any]:
        # --- PHASE 0: Cache Check ---
        entry = get_project_entry(str(self.project_root))
        if entry and mode == "fast":
            metadata = entry.get("metadata", {})
            last_summary = metadata.get("last_summary")
            summary_cache = metadata.get("summary_cache")
            
            if last_summary and summary_cache:
                try:
                    # Check for 12h freshness
                    last_time = datetime.fromisoformat(last_summary)
                    if (datetime.now() - last_time).total_seconds() < 12 * 3600:
                        summary_cache["_cache_info"] = {
                            "status": "CACHED",
                            "timestamp": last_summary,
                            "note": "Result served from project ledger (cache < 12h)."
                        }
                        return summary_cache
                except: pass # Fallback to fresh scan if date parsing fails

        # --- PHASE 1: Fresh Scan ---
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
            
            result = {
                "summary": summary,
                "hotspots": hotspots[:10],
                "health": health,
                "signals": {"circular_dependencies": graph_data["cycles"]}
            }
        else:
            result = {
                "summary": summary,
                "structure_preview": list(set([f['path'].split('/')[0] for f in files_data if '/' in f['path']]))
            }
        
        # --- PHASE 2: Update Cache ---
        result["_cache_info"] = {"status": "FRESH", "timestamp": datetime.now().isoformat()}
        save_to_registry(str(self.project_root), get_project_id(str(self.project_root)), metadata={
            "last_summary": datetime.now().isoformat(),
            "summary_cache": result
        })

        return result

    def directory_tree(self, directory: str = ".", max_depth: int = 3) -> str:
        return self.explorer.get_tree(directory, max_depth)
