import os
import pathlib
import difflib
import subprocess
import tempfile
from typing import List, Dict, Optional

class Patcher:
    """Handles atomic multi-edits and file patching."""
    
    @staticmethod
    def multi_edit(file_path: str, chunks: List[Dict[str, str]]) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Verification (Atomic)
        for i, chunk in enumerate(chunks):
            if chunk.get("target") not in content:
                raise ValueError(f"Error: Target chunk #{i+1} not found in {file_path}.")
        
        # 2. Execution
        new_content = content
        for chunk in chunks:
            new_content = new_content.replace(chunk.get("target"), chunk.get("replacement", ""))
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"Successfully applied {len(chunks)} changes to {file_path} (Atomic)."

    @staticmethod
    def get_diff(file_path: str, new_text: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            original_lines = lines[start:end]

        modified_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(original_lines, modified_lines, fromfile=file_path, tofile="modified", n=3)
        return "".join(diff)

    def apply_patch(self, target_path: str, patch_text: str) -> str:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False, encoding="utf-8") as pf:
                pf.write(patch_text)
                patch_file = pf.name
            
            result = subprocess.run(["patch", "-u", target_path, patch_file], capture_output=True, text=True)
            if result.returncode == 0: return f"Patch applied to {target_path}."
            return f"Patch failed: {result.stderr.strip()}"
        finally:
            if os.path.exists(patch_file): os.remove(patch_file)

    @staticmethod
    def diff_file_range_with_string(file_path: str, text: str, 
                                   start_line: Optional[int] = None, 
                                   end_line: Optional[int] = None) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            original_lines = lines[start:end]
            modified_lines = text.splitlines(keepends=True)
            diff = difflib.unified_diff(original_lines, modified_lines, fromfile=file_path, tofile="modified", n=3)
            return "".join(diff) or "No differences found."
        except Exception as e:
            return f"Diff failed: {str(e)}"
