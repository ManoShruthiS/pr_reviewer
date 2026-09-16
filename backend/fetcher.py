from github import Github
from config import GITHUB_TOKEN


def fetch_pr_diff(pr_url: str) -> dict:
    parts = pr_url.strip("/").split("/")
    owner = parts[3]
    repo_name = parts[4]
    pr_number = int(parts[6])

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    files = []
    for file in pr.get_files():
        files.append({
            "filename": file.filename,
            "status": file.status,
            "patch": file.patch or ""
        })

    return {
        "title": pr.title,
        "author": pr.user.login,
        "files": files
    }
