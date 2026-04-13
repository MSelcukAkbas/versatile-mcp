import os
import shutil
import time
import json
import pathlib
import subprocess
import difflib
from services.core.logger_service import setup_logger
from services.core.bin_service import BinService
from typing import List, Optional, Dict, Any

logger = setup_logger("FileService")

RESTRICTED_PATHS = {
    "windows": [
        "C:\\Windows", "C:\\Windows\\System32",
        "C:\\Program Files", "C:\\Program Files (x86)",
        "C:\\ProgramData"
    ],
    "linux": [
        "/etc", "/root", "/boot", "/dev", "/proc", "/sys", "/run"
    ]
}

def is_path_restricted(path: str) -> bool:
    """Check if the path falls under restricted system directories."""
    norm_path = os.path.normpath(path).lower()
    
    # Check Windows restrictions
    for rest in RESTRICTED_PATHS["windows"]:
        norm_rest = os.path.normpath(rest).lower()
        if norm_path == norm_rest or norm_path.startswith(norm_rest + os.sep):
            return True
            
    # Check Linux restrictions
    for rest in RESTRICTED_PATHS["linux"]:
        if norm_path == rest or norm_path.startswith(rest + "/"):
            return True
            
    return False

class FileService:
    """Advanced Service to handle secure file and directory operations."""
    
    def __init__(self, allowed_roots: List[str], ignore_svc: Optional[Any] = None):
        """Initialize with a list of allowed root directories."""
        self.allowed_roots = [pathlib.Path(p).resolve() for p in allowed_roots]
        self.bin_service = BinService(pathlib.Path(__file__).parent.parent)
        self.ignore_svc = ignore_svc
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
            str_path = str(abs_path)
            
            # Security Guard: Check restricted system paths
            if is_path_restricted(str_path):
                raise PermissionError(f"Access Denied: '{target_path}' is a restricted system path.")

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
        """
        Returns a flattened 'Indexed File Graph' optimized for AI reasoning.
        Includes semantic markers like 'language' and 'role'.
        """
        target_dir = self._resolve_path(directory)
        root_path = self.allowed_roots[0]
        
        nodes = []
        summary = {"files": 0, "dirs": 0}

        def _get_language(ext):
            map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.md': 'markdown', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
                '.html': 'html', '.css': 'css', '.sql': 'sql', '.sh': 'bash', '.ps1': 'powershell'
            }
            return map.get(ext, 'text')

        def _get_role(path, is_dir):
            p = path.lower().replace("\\", "/")
            if "main.py" in p or "app.py" in p or "index." in p: return "entrypoint"
            if "config/" in p or "settings." in p or ".env" in p or ".ignore" in p: return "config"
            if "services/" in p: return "service"
            if "tools/" in p: return "tool"
            if "models/" in p: return "model"
            if "tests/" in p or "test_" in p: return "test"
            if "readme" in p or "docs/" in p or "license" in p: return "documentation"
            if "requirements" in p or "package.json" in p: return "config"
            return "directory" if is_dir else "logic"

        def _scan(cur_path, depth=0):
            if depth > max_depth: return
            
            # rel_path for ignore check
            rel_path = os.path.relpath(cur_path, root_path)
            
            # Ensure root basename is not at the start of the path in nodes
            # If target_dir is root_path, rel_path will be "." for root
            # We want paths like "config/settings.py" not "mcp_master/config/settings.py"
            node_path = os.path.relpath(cur_path, target_dir).replace("\\", "/")
            if node_path == ".": node_path = "" # root node itself

            if self.ignore_svc and self.ignore_svc.is_ignored(rel_path, is_dir=os.path.isdir(cur_path)):
                return

            is_dir = os.path.isdir(cur_path)
            ext = os.path.splitext(cur_path)[1].lower()
            
            node = {
                "path": node_path or os.path.basename(target_dir),
                "type": "directory" if is_dir else "file",
                "depth": depth
            }
            
            if not is_dir:
                node["size"] = os.stat(cur_path).st_size # os.stat is slightly safer for race conditions but getsize is fine. Let's stick to getsize for simplicity or fix the variable.
                node["language"] = _get_language(ext)
                node["role"] = _get_role(node_path or os.path.basename(cur_path), False)
                summary["files"] += 1
            else:
                if node_path: # Don't count the root itself as a child dir in summary if we want strictly children? Usually root is included.
                    summary["dirs"] += 1
                node["role"] = _get_role(node_path or os.path.basename(cur_path), True)
                
            nodes.append(node)
            
            if is_dir:
                try:
                    for item in sorted(os.listdir(cur_path)):
                        _scan(os.path.join(cur_path, item), depth + 1)
                except PermissionError:
                    node["error"] = "Permission Denied"

        _scan(target_dir)
        
        output = {
            "root": os.path.basename(target_dir),
            "max_depth": max_depth,
            "summary": summary,
            "nodes": nodes
        }
        return json.dumps(output, indent=2)

    # --- File Operations ---
    def read_file(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, 
                  mode: str = "auto", doc_svc: Any = None) -> str:
        """
        Unified smart reader for text and rich documents.
        - auto: Detects based on extension and content.
        - text: Forces text mode with optional line range.
        - rich: Forces document extraction (PDF/DOCX/EPUB).
        """
        target_file = self._resolve_path(file_path)
        ext = os.path.splitext(target_file)[1].lower()
        
        # 1. Decision Layer: Identify Mode
        if mode == "auto":
            if ext in ['.pdf', '.docx', '.epub']:
                mode = "rich"
            else:
                mode = "text"

        # 2. Rich Mode Execution
        if mode == "rich":
            if not doc_svc:
                return "Error: Document service not available for rich content extraction."
            
            content = doc_svc.extract_text(target_file)
            if not content:
                return "Error: Could not extract text from rich document."
            
            return self._apply_smart_limits(content, limit=50000, is_rich=True)

        # 3. Text Mode Execution (with Binary Protection)
        if self._is_binary(target_file):
            return "Error: Unsupported binary file."

        stat = os.stat(target_file)
        # Full read protection (5MB)
        if not start_line and not end_line and stat.st_size > 5 * 1024 * 1024:
            return f"Error: File too large ({stat.st_size} bytes) for full read. Specify start_line/end_line."

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                if start_line or end_line:
                    lines = f.readlines()
                    start = (start_line - 1) if start_line else 0
                    end = end_line if end_line else len(lines)
                    content = "".join(lines[start:end])
                else:
                    content = f.read()
            
            # Apply formatting and limits
            processed = self._apply_smart_limits(content, limit=None) # No hard char limit for text unless requested
            return self._wrap_syntax(processed, ext)
            
        except UnicodeDecodeError:
            return "Error: File coding mismatch. Try 'rich' mode if it's a doc or check if it's binary."

    def _is_binary(self, file_path: str) -> bool:
        """Check for null bytes in the first 2KB of the file."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(2048)
                return b'\x00' in chunk
        except:
            return False

    def _apply_smart_limits(self, text: str, limit: Optional[int], is_rich: bool = False) -> str:
        """Truncate text at the nearest newline if limit is exceeded."""
        if not limit or len(text) <= limit:
            return text
            
        # Find the last newline before the limit
        truncated_point = text.rfind('\n', 0, limit)
        if truncated_point == -1:
            truncated_point = limit # Fallback to hard limit if no newline found
            
        result = text[:truncated_point]
        info = f"\n\n[Content truncated. Total: {len(text)} characters"
        if is_rich:
            info += ". Line parameters ignored for Rich Documents"
        info += "]"
        
        return result + info

    def _wrap_syntax(self, content: str, extension: str) -> str:
        """Wrap code files in markdown blocks."""
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.html': 'html', '.css': 'css', '.json': 'json',
            '.md': 'markdown', '.yml': 'yaml', '.yaml': 'yaml',
            '.sql': 'sql', '.sh': 'bash', '.ps1': 'powershell'
        }
        lang = ext_map.get(extension)
        if lang:
            return f"```{lang}\n{content}\n```"
        return content

    def read_text_file(self, file_path: str) -> str:
        return self.read_file(file_path)

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
            "name": os.path.basename(file_path),
            "extension": os.path.splitext(file_path)[1].lower(),
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

    def search_content(self, query: str, directory: str = ".", context_before: int = 5, context_after: int = 5) -> List[Dict[str, Any]]:
        """
        LLM-Optimized Semantic Code Retrieval Engine.
        Returns structured JSON with logical code blocks (line_start to line_end).
        """
        import re
        target_dir = self._resolve_path(directory)
        rg_path = self.bin_service.get_binary_path("rg")
        
        if not rg_path:
            return [{"error": "Ripgrep not found."}]

        logger.info(f"Searching semantic content: {query}")
        try:
            # -i: case-insensitive
            # --json: structured output
            cmd = [str(rg_path), "--json", "-i", query, target_dir]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            
            matches = []
            files_to_scan = {} # Cache for file lines to avoid multiple reads

            # 1. Collect all matches
            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        payload = data.get("data")
                        abs_path = payload.get("path", {}).get("text")
                        line_num = payload.get("line_number")
                        
                        rel_path = os.path.relpath(abs_path, str(self.allowed_roots[0]))
                        if rel_path not in files_to_scan:
                            files_to_scan[rel_path] = abs_path
                            
                        matches.append({
                            "file": rel_path,
                            "line": line_num,
                            "abs_path": abs_path
                        })
                except: continue

            # Limit unique files/matches for performance
            matches = matches[:50] 
            
            # 2. Extract semantic blocks
            semantic_results = []
            for m in matches:
                # Get block boundaries
                block_info = self._get_code_block(m["abs_path"], m["line"])
                
                # Scoring
                score = 0.8 # Base
                symbol_name = block_info.get("symbol") or ""
                if query.lower() in symbol_name.lower(): score += 0.2
                
                semantic_results.append({
                    "file": m["file"],
                    "symbol": block_info.get("symbol"),
                    "node_type": block_info.get("node_type", "Snippet"),
                    "score": round(score, 2),
                    "line_start": block_info.get("line_start"),
                    "line_end": block_info.get("line_end"),
                    "symbol_confidence": block_info.get("symbol_confidence", 0.0),
                    "code_preview": block_info.get("code_preview", ""),
                    "has_full_code": block_info.get("has_full_code", False)
                })

            # Sort by score
            semantic_results.sort(key=lambda x: x["score"], reverse=True)
            return semantic_results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return [{"error": str(e)}]

    def _get_code_block(self, file_path: str, match_line: int, preview_limit: int = 40) -> Dict[str, Any]:
        """Heuristic and AST fallback to find the logical code block surrounding a match line."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content_str = f.read()
            lines = content_str.splitlines(keepends=True)
            
            # 0-indexed adjustment
            idx = match_line - 1
            if idx >= len(lines): 
                return {"line_start": match_line, "line_end": match_line, "code_preview": "", "has_full_code": False, "node_type": "Snippet"}

            ext = os.path.splitext(file_path)[1].lower()
            
            start = idx
            end = idx
            symbol = None
            node_type = "Snippet"
            confidence = 0.5
            
            # 1. AST Parser Entegrasyonu (Sadece Python için)
            if ext == ".py":
                import ast
                try:
                    tree = ast.parse(content_str)
                    for node in ast.walk(tree):
                        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                            if node.lineno <= match_line <= node.end_lineno:
                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    start, end = node.lineno - 1, node.end_lineno - 1
                                    symbol = node.name
                                    node_type = "FunctionDef"
                                    confidence = 1.0
                                elif isinstance(node, ast.ClassDef):
                                    start, end = node.lineno - 1, node.end_lineno - 1
                                    symbol = node.name
                                    node_type = "ClassDef"
                                    confidence = 1.0
                except SyntaxError:
                    pass # Fallback to heuristic
            
            # 2. Heuristic Regex (AST başarısızsa veya farklı bir dilse)
            if node_type == "Snippet":
                sym_patterns = {
                    ".py": r"^\s*(def|class)\s+([a-zA-Z_]\w*)",
                    ".js": r"^\s*(async\s+)?(function|class|const|let|var)\s+([a-zA-Z_]\w*)",
                    ".ts": r"^\s*(async\s+)?(function|class|interface|type|enum|const)\s+([a-zA-Z_]\w*)",
                }
                pattern = sym_patterns.get(ext)
                
                if pattern:
                    import re
                    for i in range(idx, max(-1, idx - 40), -1):
                        m = re.search(pattern, lines[i])
                        if m:
                            start = i
                            symbol = m.group(m.lastindex)
                            node_type = "FunctionDef" if "def" in lines[i] or "function" in lines[i] else "ClassDef"
                            confidence = 0.8
                            break
                
                # Bitiş tespiti (Sadece Heuristic çalıştıysa)
                if confidence < 1.0 and pattern and start < len(lines):
                    end = min(len(lines) - 1, start + 20)
                    if ext == ".py":
                        base_indent = len(lines[start]) - len(lines[start].lstrip())
                        for j in range(start + 1, len(lines)):
                            line_stripped = lines[j].strip()
                            if not line_stripped: continue
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            if indent <= base_indent:
                                end = j - 1
                                break
                            end = j
                    else:
                        brace_count = 0
                        found_brace = False
                        for j in range(start, min(len(lines), start + 80)):
                            brace_count += lines[j].count('{') - lines[j].count('}')
                            if '{' in lines[j]: found_brace = True
                            if found_brace and brace_count <= 0:
                                end = j
                                break
                            end = j

            # Ensure the match_line is included
            end = max(end, idx)
            
            # 3. Truncation (Kesme)
            has_full_code = True
            if (end - start + 1) > preview_limit:
                has_full_code = False
                end_idx = min(len(lines), start + preview_limit)
                code_fragment = "".join(lines[start:end_idx]).strip() + "\n... [Code Truncated] ..."
            else:
                code_fragment = "".join(lines[start:end+1]).strip()
            
            return {
                "line_start": start + 1,
                "line_end": end + 1,
                "symbol": symbol,
                "node_type": node_type,
                "symbol_confidence": confidence,
                "code_preview": code_fragment,
                "has_full_code": has_full_code
            }
        except Exception as e:
            logger.error(f"Error parsing code block: {e}")
            return {
                "line_start": match_line, "line_end": match_line, 
                "code_preview": "", "has_full_code": False, "node_type": "Snippet", "symbol_confidence": 0.0
            }

    def read_multiple(self, file_paths: List[str]) -> Dict[str, str]:
        """Read multiple files at once."""
        results = {}
        for path in file_paths:
            try:
                results[path] = self.read_text_file(path)
            except Exception as e:
                results[path] = f"Error: {str(e)}"
        return results

    def diff_file_range_with_string(self, file_path: str, text: str, 
                                   start_line: Optional[int] = None, 
                                   end_line: Optional[int] = None, 
                                   context_lines: int = 3) -> str:
        """
        Bir dosyanın belirli bir satır aralığını sağlanan bir metin içeriğiyle karşılaştırır.
        """
        target_file = self._resolve_path(file_path)
        
        # 1. Dosyadaki orijinal satır aralığını oku
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                
                # Sınır kontrolleri
                start = max(0, min(start, len(lines)))
                end = max(start, min(end, len(lines)))
                
                original_lines = lines[start:end]
        except Exception as e:
            return f"Error reading file: {str(e)}"

        # 2. Karşılaştırılacak metni satırlara ayır
        modified_lines = text.splitlines(keepends=True)
        
        # 3. Etiketleri oluştur
        range_str = f"L{start_line}" if start_line else ""
        if end_line: range_str += f"-L{end_line}"
        label_a = f"{file_path} ({range_str})" if range_str else file_path
        label_b = "provided_text"

        # 4. Diff oluştur
        diff_output = list(difflib.unified_diff(
            original_lines, modified_lines,
            fromfile=label_a, tofile=label_b,
            n=context_lines
        ))

        if not diff_output:
            return "No differences found."
            
        return "".join(diff_output)

    def apply_patch(self, target_path: str, patch_text: str) -> str:
        resolved = self._resolve_path(target_path)
        original = pathlib.Path(resolved).read_text(encoding="utf-8")
        original_lines = original.splitlines(keepends=True)

        import subprocess, tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False, encoding="utf-8") as pf:
            pf.write(patch_text)
            patch_file = pf.name
        try:
            result = subprocess.run(
                ["patch", "-u", resolved, patch_file],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return f"Patch applied successfully to {target_path}."
            return f"patch command failed (rc={result.returncode}): {result.stderr.strip()}"
        except FileNotFoundError:
            return self._manual_apply_patch(resolved, original_lines, patch_text)
        finally:
            if os.path.exists(patch_file):
                os.remove(patch_file)

    def _manual_apply_patch(self, resolved_path: str, original_lines: List[str], patch_text: str) -> str:
        patched: List[str] = list(original_lines)
        offset = 0
        hunk: List[str] = []
        old_start = 0

        for line in patch_text.splitlines(keepends=True):
            if line.startswith("@@"):
                if hunk:
                    offset = self._apply_hunk(patched, hunk, old_start, offset)
                    hunk = []
                parts = line.split()
                old_range = parts[1]
                old_start = abs(int(old_range.split(",")[0]))
            elif line.startswith(("---", "+++")):
                pass
            else:
                hunk.append(line)

        if hunk:
            self._apply_hunk(patched, hunk, old_start, offset)

        pathlib.Path(resolved_path).write_text("".join(patched), encoding="utf-8")
        return f"Patch applied (manual mode) to {resolved_path}."

    def _apply_hunk(self, patched: List[str], hunk: List[str], old_start: int, offset: int) -> int:
        idx = old_start - 1 + offset
        for line in hunk:
            if line.startswith(" "):
                idx += 1
            elif line.startswith("-"):
                if idx < len(patched):
                    del patched[idx]
                    offset -= 1
            elif line.startswith("+"):
                patched.insert(idx, line[1:])
                idx += 1
                offset += 1
        return offset

