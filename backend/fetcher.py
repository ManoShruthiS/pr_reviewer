from github import Github
from config import GITHUB_TOKEN


DEMO_PRS = {
    "security": {
        "title": "feat(auth): Add user authentication and token verification",
        "author": "dev-contributor",
        "repo": "enterprise/auth-service#14",
        "files": [
            {
                "filename": "auth_service.py",
                "status": "modified",
                "patch": """@@ -1,15 +1,28 @@
 import os
+import ast
+
+JWT_SECRET_KEY = "hardcoded_super_secret_production_key_12345"
+DATABASE_PASSWORD = "root_master_password_never_expose"
+
+def verify_token(raw_payload):
+    # Unsafe token decoding
+    user_obj = eval(raw_payload)
+    return user_obj
+
+def authenticate_user(username, raw_query):
+    try:
+        query = f"SELECT * FROM users WHERE username = '{username}'"
+        return execute_query(query)
+    except:
+        pass
"""
            },
            {
                "filename": "database.py",
                "status": "modified",
                "patch": """@@ -20,10 +20,18 @@
 import sys
 import math
 
+def get_user_records(user_id, cache_list=[]):
+    cache_list.append(user_id)
+    return cache_list
+
+def calculate_stats():
+    result = undefined_variable_total + 10
+    return result
"""
            }
        ]
    },
    "bugs": {
        "title": "fix(data): Update caching and calculation helpers",
        "author": "backend-eng",
        "repo": "analytics/pipeline#8",
        "files": [
            {
                "filename": "helpers.py",
                "status": "modified",
                "patch": """@@ -5,12 +5,20 @@
 import json
 import datetime
 import collections
+from os import *
+
+def compute_metrics(items=[]):
+    items.append("new_metric")
+    total = running_sum + len(items)
+    return total
"""
            }
        ]
    },
    "clean": {
        "title": "refactor(core): Clean up logging and configuration handling",
        "author": "senior-dev",
        "repo": "platform/core-api#42",
        "files": [
            {
                "filename": "config.py",
                "status": "modified",
                "patch": """@@ -1,8 +1,12 @@
 import os
+from dotenv import load_dotenv
+
+load_dotenv()
+
+def get_database_url() -> str:
+    return os.getenv("DATABASE_URL", "sqlite:///app.db")
"""
            }
        ]
    }
}


def fetch_pr_diff(pr_url: str) -> dict:
    url_lower = pr_url.lower()

    # Check for demo / sample trigger URLs
    if "demo" in url_lower or "sample" in url_lower or "example" in url_lower:
        if "clean" in url_lower or "low" in url_lower:
            return DEMO_PRS["clean"]
        if "bug" in url_lower or "medium" in url_lower:
            return DEMO_PRS["bugs"]
        return DEMO_PRS["security"]

    # Parse standard GitHub PR URL: https://github.com/owner/repo/pull/123
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

        # Connect with token if available, otherwise unauthenticated
        g = Github(GITHUB_TOKEN) if (GITHUB_TOKEN and not GITHUB_TOKEN.startswith("your_")) else Github()
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
            "author": pr.user.login if pr.user else "collaborator",
            "repo": f"{owner}/{repo_name}#{pr_number}",
            "files": files
        }

    except Exception as e:
        # If GitHub API fails (due to rate limits, no internet, private repo, or bad URL),
        # return a realistic demo PR with a descriptive note instead of crashing
        fallback = DEMO_PRS["security"].copy()
        fallback["title"] = f"{DEMO_PRS['security']['title']} (Offline/Sample Mode)"
        fallback["note"] = f"Live GitHub fetch notice: {str(e)}"
        return fallback
