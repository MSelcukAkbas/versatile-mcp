import os
import ast
import re
import math
import pathlib
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from services.core.logger_service import setup_logger

logger = setup_logger("WorkspaceAnalyzer")

import time
from collections import deque, defaultdict, Counter

class WorkspaceAnalyzer:
    """
    Strategic multi-factor codebase analyzer.
    Performs FAST (metadata) and DEEP (AST/Ref) scans.
    Implements Weighted Hotspot Scoring and Role Inference.
    """

    def __init__(self, project_root: str, ignore_svc=None):
        self.project_root = pathlib.Path(project_root).resolve()
        self.ignore_svc = ignore_svc
        self.stats = {
            "files": 0,
            "directories": 0,
            "languages": {}
        }
        self.orchestration_map = {}
        
    def analyze(self, mode: str = "fast", max_depth: int = 5) -> Dict[str, Any]:
        """Entrypoint for workspace analysis."""
        logger.info(f"Starting {mode} analysis on: {self.project_root}")
        
        # 1. Base Scan (Always done)
        files_data = self._recursive_scan(max_depth)
        
        # Discover orchestration map (Bottom-Up)
        self._discover_orchestration_map()
        
        summary = {
            "project_root": str(self.project_root),
            "stats": self.stats,
            "mode": mode,
            "timestamp": datetime.now().isoformat(),
            "architecture": self._guess_architecture(files_data),
            "complexity": self._guess_complexity(files_data),
            "orchestration": list(self.orchestration_map.values())
        }

        # 2. Advanced Analysis
        entrypoints = self._infer_entrypoints(files_data)
        
        if mode == "deep":
            start_deep = time.time()
            dep_graph = self._build_dependency_graph(files_data)
            hotspots = self._calculate_hotspots(files_data, dep_graph)
            modules = self._group_by_modules(files_data, hotspots)
            health = self._calculate_health(dep_graph, files_data)
            patterns = self._detect_architectural_patterns(hotspots, entrypoints)
            
            logger.info(f"Performance | Deep analysis TOTAL: {time.time() - start_deep:.2f}s")
            
            return {
                "summary": summary,
                "entrypoints": entrypoints,
                "hotspots": hotspots[:10],
                "modules": modules,
                "signals": {
                    "dependency": dep_graph.get("signals", {}),
                    "architectural_patterns": patterns
                },
                "health": health
            }
        else:
            return {
                "summary": summary,
                "entrypoints": entrypoints[:3],
                "structure_preview": list(set([f['path'].split('/')[0] for f in files_data if '/' in f['path']]))
            }

    def _recursive_scan(self, max_depth: int) -> List[Dict[str, Any]]:
        """Scans the workspace, respecting .gitignore and depth limits."""
        results = []
        self.stats = {"files": 0, "directories": 0, "languages": {}}
        
        for root, dirs, files in os.walk(self.project_root):
            rel_root = os.path.relpath(root, self.project_root)
            depth = 0 if rel_root == "." else len(rel_root.split(os.sep))
            
            if depth > max_depth:
                continue

            # Filtering ignored directories
            if self.ignore_svc:
                dirs[:] = [d for d in dirs if not self.ignore_svc.is_ignored(os.path.join(rel_root, d), is_dir=True)]
                files = [f for f in files if not self.ignore_svc.is_ignored(os.path.join(rel_root, f), is_dir=False)]

            self.stats["directories"] += len(dirs)
            
            for file in files:
                file_path = pathlib.Path(root) / file
                rel_path = os.path.relpath(file_path, self.project_root).replace("\\", "/")
                ext = file_path.suffix.lower()
                
                try:
                    stat = file_path.stat()
                    file_info = {
                        "path": rel_path,
                        "abs_path": str(file_path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "extension": ext,
                        "role": "logic" # default
                    }
                    
                    # Track languages
                    lang = self._get_language(ext)
                    self.stats["languages"][lang] = self.stats["languages"].get(lang, 0) + 1
                    self.stats["files"] += 1
                    
                    results.append(file_info)
                except Exception as e:
                    logger.warning(f"Failed to stat {rel_path}: {e}")

        return results

    def _get_language(self, ext: str) -> str:
        map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.md': 'markdown', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
            '.html': 'html', '.css': 'css', '.sql': 'sql', '.sh': 'bash'
        }
        return map.get(ext, 'text')

    def _infer_entrypoints(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detects entrypoints using naming heuristics and surface scanning."""
        entries = []
        patterns = [
            (r"main\.py$", 0.9, "runtime_entry"),
            (r"app\.py$", 0.85, "runtime_entry"),
            (r"index\.(js|ts)$", 0.9, "web_entry"),
            (r"server\.(js|ts)$", 0.85, "web_entry"),
            (r"cli\.py$", 0.8, "cli_entry"),
            (r"manager\.py$", 0.7, "sys_entry")
        ]
        
        for f in files:
            for p, conf, ptype in patterns:
                if re.search(p, f["path"]):
                    # Small AST check for python entrypoints if depth < threshold
                    if f["extension"] == ".py":
                        try:
                            with open(f["abs_path"], "r", encoding="utf-8", errors="ignore") as src:
                                content = src.read()
                                if 'if __name__ == "__main__":' in content or 'FastAPI(' in content or 'Flask(' in content:
                                    conf += 0.05
                        except: pass
                    
                    entries.append({
                        "path": f["path"],
                        "confidence": min(conf, 1.0),
                        "type": ptype
                    })
        
        return sorted(entries, key=lambda x: x["confidence"], reverse=True)

    def _build_dependency_graph(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Building a real Intra-Project Dependency Graph with Module Resolution."""
        graph = {"edges": [], "fan_in": {}, "signals": {"circular_dependencies": []}}
        
        # 1. Map: module.name -> abs_path
        module_to_path = {}
        for f in files:
            path_obj = pathlib.Path(f["path"])
            # V6 FIX: Keep extension to avoid collisions between auth.js and auth.py
            mod_name = '.'.join(path_obj.parts)
            module_to_path[mod_name] = f["path"]
            
            # Also keep a legacy dot-separated name for Python style index
            legacy_name = '.'.join(path_obj.with_suffix('').parts)
            if legacy_name not in module_to_path:
                module_to_path[legacy_name] = f["path"]

        edges = []
        for i, f in enumerate(files):
            # Heartbeat Logging (every 200 files)
            if i > 0 and i % 200 == 0:
                logger.info(f"Progress | Building dependency graph: {i}/{len(files)} files scanned...")

            path = f["path"]
            imports = set()
            if f["extension"] == ".py":
                imports = self._extract_python_imports(f["abs_path"])
            elif f["extension"] in [".js", ".ts"]:
                imports = self._extract_js_imports(f["abs_path"])

            for imp in imports:
                # Resolve import to internal path if possible
                resolved_path = self._resolve_internal_path(imp, path, module_to_path)
                if resolved_path and resolved_path != path:
                    graph["edges"].append((path, resolved_path))
                    graph["fan_in"][resolved_path] = graph["fan_in"].get(resolved_path, 0) + 1
        
        graph["signals"]["circular_dependencies"] = self._find_cycles(graph["edges"])
        return graph

    def _resolve_internal_path(self, imp_name: str, scanner_path: str, module_map: Dict[str, str]) -> Optional[str]:
        """Snapshot Resolver: Resolves imports to internal files using project-relative paths."""
        if not imp_name: return None
        
        # 1. Exact match in module map
        if imp_name in module_map:
            return module_map[imp_name]
        
        # 2. Relative Resolution (JS/TS Focused)
        if imp_name.startswith('.'):
            try:
                # Current scanner file directory relative to project root
                current_dir = pathlib.Path(scanner_path).parent
                # Clean and resolve the target path relative to current dir
                parts = imp_name.split('/')
                target_path = current_dir
                for p in parts:
                    if p == '..': target_path = target_path.parent
                    elif p == '.' or not p: continue
                    else: target_path = target_path / p
                
                # Normalize target_path to be project-relative string
                # This is the FIX for the Absolute vs Relative mismatch
                rel_target = str(target_path).replace("\\", "/")
                
                # Search module_map using project-relative path
                for ext in ['.js', '.ts', '.py', '.jsx', '.tsx']:
                    potential = f"{rel_target}{ext}"
                    # Check both exact keys and values in module_map
                    for mod_key, mod_path in module_map.items():
                        if mod_path == potential or mod_path.startswith(potential):
                            return mod_path
            except: pass

        # 3. Simple String Match (Fallback for Aliases or Root Imports)
        # If imp_name is like 'services/auth', check if any file path contains it
        clean_imp = imp_name.replace('.', '/')
        for mod_key, mod_path in module_map.items():
            if clean_imp in mod_path:
                return mod_path
                
        return None

    def _extract_python_imports(self, abs_path: str) -> Set[str]:
        imports = set()
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for n in node.names: imports.add(n.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            # Handle relative level
                            prefix = "." * node.level
                            imports.add(f"{prefix}{node.module}")
        except: pass
        return imports

    def _extract_js_imports(self, abs_path: str) -> Set[str]:
        imports = set()
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = re.findall(r"(?:import|from|require)\s*['\"](.*?)['\"]", content)
                for m in matches:
                    # Logic: only internal paths usually start with . or /
                    if m.startswith('.') or any(p in m for p in ['services/', 'core/']):
                        imports.add(m.replace('/', '.').strip('.'))
        except: pass
        return imports

    def _calculate_hotspots(self, files: List[Dict], graph: Dict) -> List[Dict]:
        """Analyzes betweenness and volatility using pure File System metrics (No Git)."""
        edges = graph.get("edges", [])
        
        # 1. Graph Centrality: Betweenness
        betweenness = self._calculate_betweenness(edges, [f["path"] for f in files])
        
        # 2. Pure FS Volatility (Lightspeed)
        vol_start = time.time()
        volatility_map = self._calculate_fs_volatility([f["path"] for f in files])
        logger.info(f"Performance | Volatility calculated in {time.time() - vol_start:.2f}s")

        # V6: Orphan File Detection
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        for u, v in edges:
            out_degree[u] += 1
            in_degree[v] += 1
        
        # Add orphan patterns to signals
        orphans = [f["path"] for f in files if in_degree[f["path"]] == 0 and out_degree[f["path"]] == 0]
        if "signals" not in graph: graph["signals"] = {}
        graph["signals"]["orphaned_files"] = orphans[:20] # Limit report size
        if len(orphans) > 20: 
            logger.info(f"Architectural Sign | Found {len(orphans)} orphaned files.")

        # 3. Raw Metric Collection
        raw_metrics = {}
        for f in files:
            path = f["path"]
            raw_metrics[path] = {
                "centrality": in_degree.get(path, 0),
                "volatility": volatility_map.get(path, 0),
                "betweenness": betweenness.get(path, 0),
                "size": f["size"]
            }

        # 4. Percentile Normalization (The Fix for Flat Scoring)
        norm_metrics = self._normalize_metrics(raw_metrics)

        # 5. Final Scoring: (0.4 * Centrality) + (0.3 * Volatility) + (0.2 * Betweenness) + (0.1 * Size)
        hotspots = []
        for path, scores in norm_metrics.items():
            total_score = (
                scores["centrality"] * 0.4 +
                scores["volatility"] * 0.3 +
                scores["betweenness"] * 0.2 +
                scores["size"] * 0.1
            ) * 100
            
            risk = "low"
            if total_score > 80: risk = "high"
            elif total_score > 50: risk = "medium"
            
            hotspots.append({
                "path": path,
                "score": round(total_score, 1),
                "factors": {
                    "centrality": round(scores["centrality"], 2),
                    "volatility": round(scores["volatility"], 2),
                    "betweenness": round(scores["betweenness"], 2),
                    "size": round(scores["size"], 2)
                },
                "risk_level": risk,
                "reason": self._get_dynamic_reason(path, scores),
                "roles": [] # Will be populated during overlap analysis
            })

        return sorted(hotspots, key=lambda x: x["score"], reverse=True)

    def _detect_architectural_patterns(self, hotspots: List[Dict[str, Any]], entrypoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detects anti-patterns or specific architectural constructs (like Fat Entrypoint)."""
        signals = []
        entry_paths = {e["path"]: e["type"] for e in entrypoints}
        
        for h in hotspots:
            path = h["path"]
            # 1. Fat Entrypoint: Entrypoint is also a high-score hotspot
            if path in entry_paths:
                h["roles"].append(entry_paths[path])
                if h["score"] > 60:
                    signals.append({
                        "type": "Fat Entrypoint / Hub",
                        "path": path,
                        "severity": "high" if h["score"] > 80 else "medium",
                        "insight": f"Bootstrapper Overlap: Entrypoint ({entry_paths[path]}) acts as a strategic bottleneck."
                    })
            
            # 2. God Object / Logic Bloat
            if h["factors"]["size"] > 0.9 and h["factors"]["centrality"] > 0.8:
                h["roles"].append("core_system")
                signals.append({
                    "type": "God Object Risk",
                    "path": path,
                    "severity": "high",
                    "insight": "Concentrated Complexity: High centrality combined with massive file size."
                })

        return signals

    def _calculate_betweenness(self, edges: List[tuple], nodes: List[str]) -> Dict[str, float]:
        """Lightweight Brandes algorithm for betweenness centrality with pruning for large graphs."""
        cb = {n: 0.0 for n in nodes}
        adj = defaultdict(list)
        for u, v in edges: adj[u].append(v)
        
        # Performance Pruning: if graph is large, only analyze nodes that are part of the dependency chain
        active_nodes = set(adj.keys()) | {v for u, v in edges}
        if len(nodes) > 300:
            target_nodes = [n for n in nodes if n in active_nodes]
            logger.info(f"Pruning: Reduced centrality analysis from {len(nodes)} to {len(target_nodes)} active nodes.")
        else:
            target_nodes = nodes

        for s in target_nodes:
            stack = []
            P = {n: [] for n in nodes}
            sigma = {n: 0.0 for n in nodes}; sigma[s] = 1.0
            d = {n: -1 for n in nodes}; d[s] = 0
            q = deque([s])

            while q:
                v = q.popleft()
                stack.append(v)
                for w in adj[v]:
                    if d[w] < 0:
                        q.append(w)
                        d[w] = d[v] + 1
                    if d[w] == d[v] + 1:
                        sigma[w] += sigma[v]
                        P[w].append(v)
            
            delta = {n: 0.0 for n in nodes}
            while stack:
                w = stack.pop()
                for v in P[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != s:
                    cb[w] += delta[w]
        return cb

    def _get_service_name_from_orchestration(self, path: str) -> Optional[str]:
        """Checks if the given path belongs to a known orchestration service."""
        path = path.replace("\\", "/").strip("/")
        for svc_path, svc_name in self.orchestration_map.items():
            if path.startswith(svc_path):
                return svc_name
        return None

    def _discover_orchestration_map(self):
        """
        V8 Gold Orchestrator Discovery: Bottom-Up line parsing for 100% accuracy.
        Identifies 'context:' lines and traces back to the nearest service-defining line.
        """
        import re
        orchestration_map = {}

        # 1. Docker-Compose (Root)
        compose_path = self.project_root / "docker-compose.yml"
        if compose_path.exists():
            try:
                lines = compose_path.read_text(encoding='utf-8', errors='ignore').splitlines()
                for i, line in enumerate(lines):
                    if "context:" in line:
                        ctx_match = re.search(r"context:\s*([^\s\n\"']+)", line)
                        if ctx_match:
                            # Normalize path
                            svc_raw = ctx_match.group(1).strip().strip("'").strip('"')
                            svc_path = re.sub(r"^\./", "", svc_raw).rstrip("/").replace("\\", "/")
                            
                            # Trace UPWARDS to find the nearest line starting with exactly 2 spaces (Service Name)
                            for j in range(i - 1, -1, -1):
                                svc_match = re.match(r"^ {2}([a-zA-Z0-9_-]+):", lines[j])
                                if svc_match:
                                    svc_name = svc_match.group(1)
                                    orchestration_map[svc_path] = f"{svc_name.capitalize()}-Service"
                                    break
            except: pass

        # 2. Skaffold (Root)
        skaffold_path = self.project_root / "skaffold.yaml"
        if skaffold_path.exists():
            try:
                lines = skaffold_path.read_text(encoding='utf-8', errors='ignore').splitlines()
                for i, line in enumerate(lines):
                    if "context:" in line:
                        ctx_match = re.search(r"context:\s*([^\s\n\"']+)", line)
                        if ctx_match:
                            svc_raw = ctx_match.group(1).strip().strip("'").strip('"')
                            svc_path = re.sub(r"^\./", "", svc_raw).rstrip("/").replace("\\", "/")
                            if svc_path not in orchestration_map:
                                # Trace upwards for image name
                                for j in range(i - 1, -1, -1):
                                    img_match = re.search(r"image:\s*([^\s\n]+)", lines[j])
                                    if img_match:
                                        img_name = img_match.group(1).split('/')[-1]
                                        orchestration_map[svc_path] = f"{img_name.capitalize()}-App"
                                        break
            except: pass
        
        # Sort by path length descending (most specific matches first)
        self.orchestration_map = dict(sorted(orchestration_map.items(), key=lambda x: len(x[0]), reverse=True))
        if self.orchestration_map:
            logger.info(f"Orchestration | Mapped {len(self.orchestration_map)} refined services.")

        # 3. K8s / Helm Deployment (Scan subfolders) - Priority 3
        for k8s_dir in ["k8s", "kubernetes", "deploy", "helm"]:
            full_dir = self.project_root / k8s_dir
            if full_dir.exists() and full_dir.is_dir():
                for yaml_file in full_dir.rglob("*.yaml"):
                    try:
                        content = yaml_file.read_text(encoding='utf-8', errors='ignore')
                        # Look for container names or image paths that hint at service location
                        containers = re.findall(r"name:\s*([a-zA-Z0-9_-]+)\s+image:", content)
                        for c in containers:
                            # Search root for a folder named exactly like the container
                            for sub in ["services", "portals", "sdks/web"]:
                                if (self.project_root / sub / c).exists():
                                    p = f"{sub}/{c}"
                                    if p not in orchestration_map:
                                        orchestration_map[p] = f"{c.capitalize()}-Deployment"
                    except: pass
        
        self.orchestration_map = orchestration_map
        if orchestration_map:
            logger.info(f"Orchestration | Mapped {len(orchestration_map)} services from config files.")


    def _calculate_fs_volatility(self, paths: List[str]) -> Dict[str, float]:
        """
        Pure File System Volatility Engine.
        Uses mtime (recency) and size (complexity) as reliable proxies for risk.
        Zero dependencies, zero waiting.
        """
        volatility = {p: 0.0 for p in paths}
        current_time = time.time()
        
        for p in paths:
            try:
                full_path = self.project_root / p
                stat = full_path.stat()
                
                # Recency factor: Decay based on days since modification
                # Formula: 1 / (log2(days + 2)) -> smooth decay
                days_since_mod = (current_time - stat.st_mtime) / 86400
                recency_score = 1.0 / (math.log2(max(0, days_since_mod) + 2))
                
                # Complexity proxy: File size (Log scale)
                size_score = math.log10(stat.st_size + 1)
                
                volatility[p] = recency_score * size_score
            except:
                volatility[p] = 0.0
                
        # Normalize to 0-1
        max_val = max(volatility.values()) if volatility.values() else 0
        if max_val > 0:
            for p in volatility:
                volatility[p] = volatility[p] / max_val
                
        return volatility

    def _normalize_metrics(self, raw_data: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Percentile Normalization (The Fix for Flat Scoring)."""
        metrics = ["centrality", "volatility", "betweenness", "size"]
        results = {path: {} for path in raw_data.keys()}
        
        for m in metrics:
            values = sorted([(path, data[m]) for path, data in raw_data.items()], key=lambda x: x[1])
            count = len(values)
            if count == 0: continue
            
            for rank, (path, val) in enumerate(values):
                # Rank-based percentile normalization
                results[path][m] = rank / (count - 1) if count > 1 else 1.0
        
        return results

    def _get_dynamic_reason(self, path: str, scores: Dict[str, float]) -> str:
        """Generates architectural context using multi-factor combination logic."""
        c, v, b, s = scores["centrality"], scores["volatility"], scores["betweenness"], scores["size"]

        # 1. Architectural Anchor (En kritik düğüm)
        if c > 0.8 and b > 0.8:
            return "Mimari Çıpa: Sistemin hem en çok kullanılan hem de en stratejik geçiş noktası."
        
        # 2. Unstable Core (Tehlikeli çekirdek)
        if v > 0.8 and (c > 0.6 or b > 0.6):
            return "Kararsız Çekirdek: Stratejik önemi yüksek ancak çok sık değişen riskli bileşen."
        
        # 3. Critical Chokepoint (Stratejik darboğaz)
        if b > 0.8 and v > 0.7:
            return "Stratejik Darboğaz: Modüller arası köprü vazifesi görüyor ve aktif olarak modifiye ediliyor."

        # 4. Isolated Bridge (Gizli bağımlılık)
        if b > 0.8 and c < 0.3:
            return "Gizli Köprü: Doğrudan kullanımı az olsa da katmanlar arası kritik bir bağ sağlıyor."

        # 5. Bloated Utility (Hantal yapı)
        if s > 0.8 and c < 0.3:
            return "Hantal Bileşen: Dosya boyutu büyük fakat sistem geneline etkisi sınırlı (Refaktör adayı)."

        # 6. Maintenance Hotspot (Bakım odağı)
        if v > 0.8 and s > 0.7:
            return "Bakım Odağı: Sürekli büyüyen ve sık müdahale gerektiren karmaşık nokta."

        # 7. Core Node (Standart çekirdek)
        if c > 0.7:
            return "Merkezi Servis: Projenin birçok noktasına hizmet veren temel bileşen."

        # 8. Structural Module (Stratejik modül)
        if b > 0.6:
            return "Stratejik Modül: Mimari bütünlüğü sağlayan önemli bir yapı taşı."
        
        return "Mimari bileşen"

    def _find_cycles(self, edges: List[tuple]) -> List[List[str]]:
        """Simplified cycle detection."""
        adj = {}
        for u, v in edges:
            if u not in adj: adj[u] = []
            adj[u].append(v)
            
        cycles = []
        visited = set()
        stack = []

        def dfs(node):
            if node in stack:
                start_idx = stack.index(node)
                cycles.append(stack[start_idx:] + [node])
                return
            if node in visited:
                return
            
            visited.add(node)
            stack.append(node)
            if node in adj:
                for neighbor in adj[node]:
                    dfs(neighbor)
            stack.pop()

        for node in list(adj.keys()):
            dfs(node)
            
        return cycles[:5] # Limit to 5 cycles

    def _calculate_health(self, graph: Dict[str, Any], files: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculates coupling and modularity scores."""
        total_files = len(files)
        total_edges = len(graph["edges"])
        if total_files == 0: return {"coupling_score": 0, "modularity_score": 0}
        
        # Average coupling: edges per file
        avg_coupling = total_edges / total_files
        norm_coupling = 1.0 / (1.0 + avg_coupling) # Higher is better (less coupled)
        
        # Modularity: unique extensions vs file count
        unique_exts = len(set([f["extension"] for f in files]))
        modularity = (unique_exts / total_files) * 0.5 + (norm_coupling * 0.5)
        
        return {
            "coupling_score": round(norm_coupling, 2),
            "modularity_score": round(modularity, 2)
        }

    def _get_hotspot_reason(self, path: str, score: float) -> str:
        if score > 80: return "Critical central dependency node"
        if "service" in path.lower(): return "Frequent business logic container"
        if "config" in path.lower(): return "Sensitive configuration anchor"
        return "Aggregated complexity hotspot"

    def _group_by_modules(self, files: List[Dict], hotspots: List[Dict]) -> List[Dict]:
        """Groups files into high-level architectural modules/services."""
        module_stats = defaultdict(lambda: {"files": 0, "hotspots": 0, "role": "unknown"})
        
        for f in files:
            path = f["path"].replace("\\", "/")
            path_obj = pathlib.Path(path)
            
            # V8: Check for orchestrator-defined service first
            module_name = self._get_service_name_from_orchestration(path)
            
            # Fallback 1: Strong module signals (package.json, pyproject.toml etc)
            if not module_name:
                # We check the directory tree for anchors upwards
                current = path_obj.parent
                while str(current) != "." and len(current.parts) > 0:
                    # Look for manifest in this dir
                    for manifest in ["package.json", "pyproject.toml", "requirements.txt", "go.mod", "Dockerfile"]:
                        if (self.project_root / current / manifest).exists():
                            module_name = current.name
                            break
                    if module_name: break
                    current = current.parent

            # Fallback 2: Top-level directory
            if not module_name:
                parts = path_obj.parts
                module_name = parts[0] if len(parts) > 1 else "root"
            
            is_hotspot = any(h["path"] == f["path"] and h["risk_level"] == "high" for h in hotspots)
            
            module_stats[module_name]["files"] += 1
            if is_hotspot:
                module_stats[module_name]["hotspots"] += 1
        
        # Infer role based on folder names
        for name, m in module_stats.items():
            if name in ["services", "logic", "core"]: m["role"] = "core_system"
            elif name in ["api", "routes", "controllers"]: m["role"] = "interface_layer"
            elif name in ["models", "db", "schemas"]: m["role"] = "data_layer"
            elif name in ["tests", "spec"]: m["role"] = "quality_assurance"
            
        return sorted([{"name": k, **v} for k, v in module_stats.items()], key=lambda x: x["files"], reverse=True)

    def _guess_architecture(self, files: List[Dict[str, Any]]) -> str:
        paths = [f["path"].lower() for f in files]
        if any("services/" in p for p in paths) and any("models/" in p for p in paths):
            return "Layered Architecture (Service-Model)"
        if any("app/" in p for p in paths) and any("index." in p for p in paths):
            return "Modular Web Architecture"
        return "Monolithic or Script-based"

    def _guess_complexity(self, files: List[Dict[str, Any]]) -> str:
        count = len(files)
        if count > 200: return "High"
        if count > 50: return "Medium"
        return "Low"
    def _guess_complexity(self, files: List[Dict[str, Any]]) -> str:
        """Determines project complexity based on file count and density."""
        count = len(files)
        if count > 500: return "High"
        if count > 100: return "Moderate"
        return "Low"
