import json
import os
from typing import Optional, Dict, List
from fastmcp import FastMCP

def register_github_tools(mcp: FastMCP, github_svc, diag_svc):
    @mcp.tool()
    async def github_api_push(repo_name: str, branch: str, files_json: str, commit_message: str) -> str:
        """
        Push files to GitHub using the API (Pure API, no local git required).
        files_json: JSON string of Dict {path: content}
        """
        try:
            # Integrated diagnostic check
            err = await diag_svc.check_tool_dependency("github_api_push")
            if err: return err
            
            files = json.loads(files_json)
            sha = github_svc.api_push(repo_name, branch, files, commit_message)
            return f"Successfully pushed. New commit SHA: {sha}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def github_api_diff(repo_name: str, base: str, head: str) -> str:
        try:
            err = await diag_svc.check_tool_dependency("github_api_diff")
            if err: return err
            diff_url = github_svc.api_get_diff(repo_name, base, head)
            return f"Diff comparison available at: {diff_url}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def github_api_get_file(repo_name: str, path: str, ref: str = "main") -> str:
        try:
            content = github_svc.api_get_file_content(repo_name, path, ref)
            return content
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def github_api_sync(repo_name: str, branch: str, local_dir: str) -> str:
        try:
            err = await diag_svc.check_tool_dependency("github_api_sync")
            if err: return err
            github_svc.api_sync(repo_name, branch, local_dir)
            return f"Successfully synced repo {repo_name} (branch: {branch}) to {local_dir}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    async def github_manage_issues(repo_name: str, action: str, title: Optional[str] = None, body: Optional[str] = None, issue_number: Optional[int] = None) -> str:
        try:
            repo = github_svc._get_repo(repo_name)
            if action == 'list':
                issues = repo.get_issues(state='open')
                return "\n".join([f"#{i.number}: {i.title}" for i in issues[:10]])
            elif action == 'create':
                issue = repo.create_issue(title=title, body=body)
                return f"Issue created: #{issue.number}"
            elif action == 'comment':
                issue = repo.get_issue(number=issue_number)
                issue.create_comment(body)
                return f"Commented on issue #{issue_number}"
            elif action == 'close':
                issue = repo.get_issue(number=issue_number)
                issue.edit(state='closed')
                return f"Closed issue #{issue_number}"
            else:
                return "Invalid action."
        except Exception as e:
            return f"Error: {str(e)}"
