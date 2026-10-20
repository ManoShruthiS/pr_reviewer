# ==============================================================================
# FILE: fetcher.py
# PURPOSE: Downloads code and details from GitHub when a user submits a Pull Request link.
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like a mail delivery person or courier.
# 1. The user gives you an address: "https://github.com/torvalds/linux/pull/10"
# 2. This file breaks down the address to find:
#    - Who owns it? (e.g. 'torvalds')
#    - What is the project? (e.g. 'linux')
#    - What is the Pull Request number? (e.g. '10')
# 3. It travels to GitHub over the internet, knocks on GitHub's door,
#    and downloads all the files and code changes that the developer submitted.
# 4. It neatly packages everything into a box and hands it to our security scanner!
# ==============================================================================

# 'Github' comes from the 'PyGithub' library.
# It is a pre-made tool that makes it super easy for Python to talk to GitHub's official API.
from github import Github

# Import our optional secret token from config.py
from config import GITHUB_TOKEN


# This is the main function that takes a web URL and downloads the PR information.
def fetch_pr_diff(pr_url: str) -> dict:
    """
    Direct live GitHub Pull Request fetcher.
    Parses PR URL, retrieves changed files and unified diff patches from GitHub API.
    """
    try:
        # STEP 1: BREAK DOWN THE URL TO EXTRACT OWNER, REPO, AND PR NUMBER
        # Example URL: "https://github.com/pallets/flask/pull/42"
        # We clean off any trailing slashes and split the text wherever there is a "/"
        parts = pr_url.strip().strip("/").split("/")

        # Look through the pieces to find where "github.com" is located
        gh_idx = -1
        for i, part in enumerate(parts):
            if "github.com" in part:
                gh_idx = i
                break

        # If we found "github.com", the items right after it tell us:
        # parts[gh_idx + 1] -> The repository owner (e.g. "pallets")
        # parts[gh_idx + 2] -> The project name (e.g. "flask")
        # parts[gh_idx + 4] -> The PR number (e.g. 42)
        if gh_idx != -1 and len(parts) >= gh_idx + 4:
            owner = parts[gh_idx + 1]
            repo_name = parts[gh_idx + 2]
            pr_number = int(parts[gh_idx + 4])
        else:
            # Fallback index positions if URL format is slightly different
            owner = parts[3]
            repo_name = parts[4]
            pr_number = int(parts[6])

        # STEP 2: CONNECT TO GITHUB
        # If the user put a GITHUB_TOKEN in their settings, we use it for higher speeds (5,000 req/hr).
        # Otherwise, we connect anonymously for free (60 requests per hour).
        g = Github(GITHUB_TOKEN) if (GITHUB_TOKEN and not GITHUB_TOKEN.startswith("your_")) else Github()

        # STEP 3: ACCESS THE SPECIFIC REPOSITORY AND PULL REQUEST
        # Find the project on GitHub:
        repo = g.get_repo(f"{owner}/{repo_name}")
        # Open the specific Pull Request:
        pr = repo.get_pull(pr_number)

        # STEP 4: DOWNLOAD EVERY FILE THAT WAS CHANGED IN THIS PULL REQUEST
        files = []
        for file in pr.get_files():
            content = ""
            try:
                # If the file was not deleted, fetch the full authentic code from GitHub
                if file.status != "removed":
                    fc = repo.get_contents(file.filename, ref=pr.head.sha)
                    # Convert the raw computer bytes into readable human text (UTF-8)
                    if hasattr(fc, "decoded_content"):
                        content = fc.decoded_content.decode("utf-8", errors="replace")
            except Exception:
                # If fetching full content fails (e.g. binary image file), continue gracefully
                pass

            # Add this file's details into our files list
            files.append({
                "filename": file.filename,  # Name and path of the file (e.g. "app/main.py")
                "status": file.status,      # Status (e.g. "modified", "added", "removed")
                "patch": file.patch or "",  # The Git diff (+ and - lines showing what changed)
                "content": content          # The full text code inside the file
            })

        # STEP 5: PACKAGE AND RETURN THE RESULTS
        return {
            "title": pr.title,                                           # Title of the PR
            "author": pr.user.login if pr.user else "collaborator",     # Who wrote the code
            "repo": f"{owner}/{repo_name}#{pr_number}",                  # Full repo identifier
            "files": files                                               # List of all changed files
        }

    # STEP 6: FRIENDLY ERROR HANDLING
    # If anything goes wrong (e.g. bad link or internet is down), explain in simple English!
    except Exception as e:
        err_str = str(e)

        # 404 Error: The web page doesn't exist
        if "404" in err_str:
            raise ValueError(f"GitHub Pull Request not found (404). Please ensure the repository is public and PR #{pr_number if 'pr_number' in locals() else 'specified'} exists.")

        # 403 Error: Too many requests without an API token
        elif "403" in err_str or "rate limit" in err_str.lower():
            raise ValueError("GitHub API rate limit exceeded (60 requests/hr for unauthenticated requests). Please configure GITHUB_TOKEN in backend/.env for up to 5,000 requests/hr.")

        # Internet or Wi-Fi disconnected
        elif "connection" in err_str.lower() or "resolve" in err_str.lower():
            raise ValueError("Network error: Unable to connect to GitHub API. Please check your internet connection.")

        # Any other unexpected issue
        else:
            raise ValueError(f"GitHub PR fetch failed: {err_str}")
