import os
from github import Github, InputGitTreeElement
from typing import List, Dict, Optional

class GitHubService:
    def __init__(self, logger_service):
        self.logger = logger_service
        self.token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        self.gh = Github(self.token) if self.token else None
        self.status = "Offline"
        self.details = "Service not initialized"
        
        if not self.token:
            self.logger.warning("GitHub | GITHUB_PERSONAL_ACCESS_TOKEN not set. GitHub tools will be limited.")
            self.status = "Limited"
            self.details = "No token provided"
        else:
            self._validate_token()

    def _validate_token(self):
        """Checks if the token is valid and what permissions it has."""
        try:
            user = self.gh.get_user()
            self.status = "Online"
            self.details = f"Authenticated as: {user.login}"
            self.logger.info(f"GitHub | {self.details}")
        except Exception as e:
            self.status = "Unauthorized"
            self.details = str(e)
            self.logger.error(f"GitHub | Token Validation Failed: {e}")
            self.gh = None

    def _get_repo(self, repo_name: str):
        if not self.gh:
            raise ValueError("GitHub client not initialized. Check GITHUB_PERSONAL_ACCESS_TOKEN.")
        return self.gh.get_repo(repo_name)

    def get_status(self) -> Dict[str, str]:
        """Returns the current status for diagnostics."""
        if not self.token:
            return {"status": "Limited", "details": "No token provided. Tools are inactive."}
        return {"status": self.status, "details": self.details}

    def api_push(self, repo_name: str, branch: str, files: Dict[str, str], commit_message: str):
        """
        Pushes multiple files to a branch via GitHub Git Data API (Pure API, no local git).
        files: Dict where key is file path in repo, value is text content.
        """
        repo = self._get_repo(repo_name)
        
        # 1. Get the latest commit of the branch
        try:
            ref = repo.get_git_ref(f"heads/{branch}")
            base_commit = repo.get_git_commit(ref.object.sha)
            base_tree = base_commit.tree
        except Exception as e:
            self.logger.error(f"Error getting branch ref: {e}")
            raise

        # 2. Create blobs and tree elements
        element_list = []
        for path, content in files.items():
            element = InputGitTreeElement(path, '100644', 'blob', content=content)
            element_list.append(element)

        # 3. Create a new tree
        tree = repo.create_git_tree(element_list, base_tree)

        # 4. Create the commit
        commit = repo.create_git_commit(commit_message, tree, [base_commit])

        # 5. Update the reference
        ref.edit(commit.sha)
        
        return commit.sha

    def api_get_diff(self, repo_name: str, base: str, head: str) -> str:
        repo = self._get_repo(repo_name)
        comparison = repo.compare(base, head)
        return comparison.diff_url

    def api_get_file_content(self, repo_name: str, path: str, ref: str = "main") -> str:
        repo = self._get_repo(repo_name)
        content_file = repo.get_contents(path, ref=ref)
        return content_file.decoded_content.decode("utf-8")

    def api_sync(self, repo_name: str, branch: str, local_dir: str):
        repo = self._get_repo(repo_name)
        contents = repo.get_contents("", ref=branch)
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path, ref=branch))
            else:
                dest_path = os.path.join(local_dir, file_content.path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(file_content.decoded_content)
        return True
