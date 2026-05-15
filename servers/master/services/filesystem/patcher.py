from typing import Optional, List, Dict
from services.core.logger_service import setup_logger

class Patcher:
    """Handles file patching and diff operations."""

    def __init__(self):
        self.logger = setup_logger("Infrastructure.Patcher")

    async def multi_edit(self, file_path: str, chunks: List[Dict[str, str]]) -> bool:
        """Apply multiple find-and-replace edits atomically."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Validate all targets exist before making any changes
            for chunk in chunks:
                if chunk['target'] not in content:
                    self.logger.error(f"Target not found in {file_path}: {chunk['target'][:100]}")
                    return False

            # Apply all replacements
            for chunk in chunks:
                content = content.replace(chunk['target'], chunk['replacement'])

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Multi-edit applied to {file_path} ({len(chunks)} replacements)")
            return True
        except Exception as e:
            self.logger.error(f"Multi-edit failed: {str(e)}")
            return False

    def diff_file_range_with_string(self, file_path: str, text: str,
                                    start_line: Optional[int] = None,
                                    end_line: Optional[int] = None,
                                    context_lines: int = 3) -> str:
        """Compare a line range of a file against provided text, return unified diff."""
        import difflib
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()

            s = (start_line - 1) if start_line else 0
            e = end_line if end_line else len(all_lines)
            original = all_lines[s:e]
            proposed = [l if l.endswith('\n') else l + '\n' for l in text.splitlines()]

            diff = list(difflib.unified_diff(
                original, proposed,
                fromfile=f"{file_path} (lines {s+1}-{e})",
                tofile="proposed",
                n=context_lines,
            ))
            return "".join(diff) if diff else "No differences found."
        except Exception as e:
            self.logger.error(f"Diff failed: {e}")
            return f"Error: {e}"
