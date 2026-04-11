import os
import subprocess
from typing import Dict, List, Optional

class GitService:
    """Service to handle local Git CLI operations."""
    
    def __init__(self, logger_service, bin_service):
        self.logger = logger_service
        self.bin = bin_service
        self.is_available = self.bin.is_tool_available("git")
        self.git_path = self.bin.get_binary_path("git")

    def _run_git(self, args: List[str], cwd: Optional[str] = None) -> str:
        """Run a git command and return the output."""
        if not self.is_available:
            raise RuntimeError("Git CLI is not available on this system.")
        
        cmd = [str(self.git_path)] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() or str(e)
            self.logger.error(f"Git | Command failed: {' '.join(cmd)} | Error: {error_msg}")
            raise RuntimeError(f"Git command failed: {error_msg}")

    def push(self, cwd: str, commit_message: str, branch: Optional[str] = None) -> str:
        """Stage all, commit, and push."""
        self.logger.info(f"Git | Pushing changes in {cwd}...")
        
        # 1. Add all
        self._run_git(["add", "."], cwd=cwd)
        
        # 2. Commit (allow empty to prevent errors if nothing changed)
        self._run_git(["commit", "--allow-empty", "-m", commit_message], cwd=cwd)
        
        # 3. Push
        target_branch = branch or self.get_current_branch(cwd)
        output = self._run_git(["push", "origin", target_branch], cwd=cwd)
        
        return f"Successfully pushed to {target_branch}. {output}"

    def pull(self, cwd: str, branch: Optional[str] = None) -> str:
        """Pull latest changes."""
        target_branch = branch or self.get_current_branch(cwd)
        self.logger.info(f"Git | Pulling {target_branch} in {cwd}...")
        return self._run_git(["pull", "origin", target_branch], cwd=cwd)

    def diff(self, cwd: str, base: str = "HEAD") -> str:
        """Get diff."""
        return self._run_git(["diff", base], cwd=cwd)

    def get_status(self, cwd: str) -> str:
        """Get git status."""
        return self._run_git(["status", "--short"], cwd=cwd)

    def get_current_branch(self, cwd: str) -> str:
        """Get name of the current branch."""
        try:
            return self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
        except:
            return "main" # Fallback
