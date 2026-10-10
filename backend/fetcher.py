from github import Github
from config import GITHUB_TOKEN


def fetch_pr_diff(pr_url: str) -> dict:
    """
    Direct live GitHub Pull Request fetcher.
    Parses PR URL, retrieves changed files and unified diff patches from GitHub API.
    """
    try:
        parts = pr_url.strip().strip("/").split("/")
        # Find index of github.com
        gh_idx = -1
        for i, part in enumerate(parts):
            if "github.com" in part:
                gh_idx = i
                break

        if gh_idx != -1 and len(parts) >= gh_idx + 4:
            owner = parts[gh_idx + 1]
            repo_name = parts[gh_idx + 2]
            pr_number = int(parts[gh_idx + 4])
        else:
            owner = parts[3]
            repo_name = parts[4]
            pr_number = int(parts[6])

        # Connect with token if available, otherwise unauthenticated (60 req/hr)
        g = Github(GITHUB_TOKEN) if (GITHUB_TOKEN and not GITHUB_TOKEN.startswith("your_")) else Github()
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)

        files = []
        for file in pr.get_files():
            content = ""
            try:
                # Fetch full authentic source file at PR head commit to avoid patch indentation artifacts
                if file.status != "removed":
                    fc = repo.get_contents(file.filename, ref=pr.head.sha)
                    if hasattr(fc, "decoded_content"):
                        content = fc.decoded_content.decode("utf-8", errors="replace")
            except Exception:
                pass

            files.append({
                "filename": file.filename,
                "status": file.status,
                "patch": file.patch or "",
                "content": content
            })

        return {
            "title": pr.title,
            "author": pr.user.login if pr.user else "collaborator",
            "repo": f"{owner}/{repo_name}#{pr_number}",
            "files": files
        }

    except Exception as e:
        err_str = str(e)
        if "404" in err_str:
            raise ValueError(f"GitHub Pull Request not found (404). Please ensure the repository is public and PR #{pr_number if 'pr_number' in locals() else 'specified'} exists.")
        elif "403" in err_str or "rate limit" in err_str.lower():
            raise ValueError("GitHub API rate limit exceeded (60 requests/hr for unauthenticated requests). Please configure GITHUB_TOKEN in backend/.env for up to 5,000 requests/hr.")
        elif "connection" in err_str.lower() or "resolve" in err_str.lower():
            raise ValueError("Network error: Unable to connect to GitHub API. Please check your internet connection.")
        else:
            raise ValueError(f"GitHub PR fetch failed: {err_str}")
