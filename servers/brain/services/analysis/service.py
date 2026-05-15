import os
import time
from .scanner import FileScanner


class WorkspaceAnalyzerService:
    """
    Consolidated analyzer for workspace structure and architecture.
    Provides high-level insights without deep indexing.
    """

    def __init__(self, ignore_svc):
        self.ignore_svc = ignore_svc

    def analyze(self, project_root: str, max_depth: int = 5) -> dict:
        """
        Analyzes the workspace to produce a structured summary.
        Includes language distribution, recently modified files, and directory structure.
        """
        spec = self.ignore_svc.get_spec()
        scanner = FileScanner(spec)
        files = scanner.scan(project_root, max_depth)

        lang_dist = self._get_lang_dist(files)
        top_langs = sorted(lang_dist.items(), key=lambda x: x[1], reverse=True)[:5]

        # Recently modified files (last 7 days)
        cutoff = time.time() - 7 * 86400
        recent = sorted(
            [f for f in files if f.get("mtime", 0) > cutoff],
            key=lambda x: x.get("mtime", 0),
            reverse=True
        )[:10]

        # Largest files
        largest = sorted(files, key=lambda x: x["size"], reverse=True)[:5]

        # Top-level directory structure
        top_dirs = {}
        for f in files:
            parts = f["path"].replace("\\", "/").split("/")
            top = parts[0] if len(parts) > 1 else "."
            top_dirs[top] = top_dirs.get(top, 0) + 1

        return {
            "root": project_root,
            "stats": {
                "total_files": len(files),
                "total_size_kb": round(sum(f["size"] for f in files) / 1024, 1),
                "language_distribution": lang_dist,
                "top_languages": [{"ext": e, "count": c} for e, c in top_langs],
            },
            "structure": {
                "top_level_dirs": dict(sorted(top_dirs.items(), key=lambda x: x[1], reverse=True)),
            },
            "recently_modified": [
                {"path": f["path"], "size_kb": round(f["size"] / 1024, 1)}
                for f in recent
            ],
            "largest_files": [
                {"path": f["path"], "size_kb": round(f["size"] / 1024, 1)}
                for f in largest
            ],
        }

    def _get_lang_dist(self, files: list) -> dict:
        """Calculates file extension distribution."""
        dist = {}
        for f in files:
            ext = f["type"] or "no-ext"
            dist[ext] = dist.get(ext, 0) + 1
        return dist
