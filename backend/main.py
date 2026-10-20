# ==============================================================================
# FILE: main.py
# PURPOSE: The central brain and web server of our entire application.
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like the head chef in a restaurant kitchen:
# 1. The customer (the web browser) places an order by sending a GitHub PR link.
# 2. This file receives the order and coordinates the other helper files:
#    - Calls fetcher.py to download the code from GitHub.
#    - Calls language_detector.py to see what languages were used.
#    - Calls analyzer.py to hunt down bugs and security vulnerabilities.
#    - Calls ai_explainer.py to explain the issues and generate code fixes.
#    - Calls risk_scorer.py to calculate a final score from 0 to 100.
#    - Calls database.py to save the results.
# 3. Finally, it serves the beautifully finished report back to the user's screen!
# ==============================================================================

# ------------------------------------------------------------------------------
# STEP 1: IMPORT NECESSARY TOOLS AND LIBRARIES
# ------------------------------------------------------------------------------
# 'json' helps Python turn text strings into computer objects and vice-versa
import json

# 'os' and 'Path' help Python find where files and folders are saved on your computer
import os
from pathlib import Path

# 'FastAPI' is the modern, super-fast web server framework that handles web requests.
# 'HTTPException' allows us to send clear error messages back to the user if something fails.
from fastapi import FastAPI, HTTPException

# 'CORSMiddleware' ensures that your web browser is allowed to communicate with this server.
from fastapi.middleware.cors import CORSMiddleware

# 'StaticFiles' and 'FileResponse' allow FastAPI to serve our HTML, CSS, and JS web page files directly.
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 'BaseModel' comes from Pydantic. It verifies that data sent to our server has the correct format.
from pydantic import BaseModel

# --- IMPORT OUR PROJECT'S CUSTOM HELPER MODULES ---
from fetcher import fetch_pr_diff                 # Downloads the pull request code from GitHub
from analyzer import analyze_files                # Scans code for security holes and functional bugs
from ai_explainer import explain_issues           # Provides human-friendly explanations and fixes
from risk_scorer import calculate_risk_score      # Calculates the 0-100 risk score
from database import init_db, save_review, get_all_reviews, get_review_by_id  # Database operations
from config import GITHUB_TOKEN, OPENAI_API_KEY  # Reads your secret tokens from the .env file
from language_detector import analyze_pr_coverage # Checks which languages are in the PR


# ------------------------------------------------------------------------------
# STEP 2: CREATE THE FASTAPI WEB SERVER APPLICATION
# ------------------------------------------------------------------------------
# We initialize our FastAPI app with a title and description.
app = FastAPI(
    title="AI-Powered Intelligent Code Review and Risk Analysis System",
    description="Backend API for automated GitHub PR analysis, static security/bug scanning, and AI explanations."
)

# Set up CORS (Cross-Origin Resource Sharing).
# This tells the computer: "Allow our frontend web page to make API requests to this backend without blocking."
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Allow requests from any web page origin
    allow_credentials=True, # Allow cookies or authentication if needed
    allow_methods=["*"],     # Allow GET, POST, and other web request methods
    allow_headers=["*"],     # Allow standard web headers
)

# Start and reset our in-memory SQLite database so every fresh run begins cleanly
init_db()

# Find the exact folder path where the frontend (HTML, CSS, JS) files live on your computer
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ------------------------------------------------------------------------------
# STEP 3: DEFINE THE REQUEST FORMAT FROM THE BROWSER
# ------------------------------------------------------------------------------
# When the user types a GitHub PR URL on the webpage and clicks "Analyze",
# this model ensures the incoming data has a valid "pr_url" text field.
class ReviewRequest(BaseModel):
    pr_url: str


# ------------------------------------------------------------------------------
# STEP 4: THE MAIN REVIEW API ROUTE (POST /review)
# ------------------------------------------------------------------------------
# This is the most important function in the entire project!
# When the frontend clicks the "Analyze" button, it sends the URL here.
@app.post("/review")
def review_pr(request: ReviewRequest):
    # 1. Clean up the URL by stripping off any accidentally typed spaces
    pr_url = request.pr_url.strip()
    if not pr_url:
        raise HTTPException(status_code=400, detail="Pull request URL cannot be empty.")

    try:
        # STEP 4.1: Download PR details and changed files from GitHub
        pr_data = fetch_pr_diff(pr_url)
        files = pr_data.get("files", [])

        # STEP 4.2: Detect programming languages and compute coverage % (e.g. 100% Python)
        coverage_data = analyze_pr_coverage(files)

        # STEP 4.3: Run static security and bug analysis (Bandit, Pyflakes, AST, and regex rules)
        raw_issues = analyze_files(files)

        # STEP 4.4: Add AI explanations and recommended code fixes for every detected issue
        issues = explain_issues(raw_issues, files)

        # STEP 4.5: Calculate the final Risk Score (0 = Clean, 100 = Dangerous)
        risk_score = calculate_risk_score(issues)

        # STEP 4.6: Save this review into our database so it appears in the history log
        review_id = save_review(
            pr_url=pr_url,
            pr_title=pr_data.get("title", "GitHub Pull Request"),
            risk_score=risk_score,
            issues_json=json.dumps(issues)
        )

        # STEP 4.7: Return the complete results back to the frontend web browser!
        return {
            "id": review_id,
            "prUrl": pr_url,
            "prTitle": pr_data.get("title", "GitHub Pull Request"),
            "author": pr_data.get("author", "Developer"),
            "repo": pr_data.get("repo", "github/repository"),
            "riskScore": risk_score,
            "issues": issues,
            "coverage": coverage_data,
            "fileCount": len(files),
            "note": pr_data.get("note", "")
        }

    # If the user typed an invalid link or GitHub blocked the request, show an understandable error
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


# ------------------------------------------------------------------------------
# STEP 5: HISTORY API ROUTE (GET /history)
# ------------------------------------------------------------------------------
# Returns a list of past reviews so users can see previous audits in the sidebar.
@app.get("/history")
def get_history():
    reviews = get_all_reviews()
    return [
        {
            "id": r.id,
            "pr_url": r.pr_url,
            "pr_title": r.pr_title,
            "risk_score": r.risk_score,
            "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at)
        }
        for r in reviews
    ]


# ------------------------------------------------------------------------------
# STEP 6: SINGLE REVIEW API ROUTE (GET /review/{review_id})
# ------------------------------------------------------------------------------
# If the user clicks on a past review from their history list, this fetches its details.
@app.get("/review/{review_id}")
def get_single_review(review_id: int):
    review = get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    issues = []
    if review.issues_json:
        try:
            issues = json.loads(review.issues_json)
        except Exception:
            issues = []

    return {
        "id": review.id,
        "prUrl": review.pr_url,
        "prTitle": review.pr_title,
        "riskScore": review.risk_score,
        "issues": issues,
        "created_at": review.created_at.isoformat() if hasattr(review.created_at, "isoformat") else str(review.created_at)
    }


# ------------------------------------------------------------------------------
# STEP 7: SYSTEM STATUS API ROUTE (GET /api/status)
# ------------------------------------------------------------------------------
# Informs the frontend whether the backend is online and what security scanners are active.
@app.get("/api/status")
def get_status():
    has_github = bool(GITHUB_TOKEN and not GITHUB_TOKEN.startswith("your_"))
    has_openai = bool(OPENAI_API_KEY and not OPENAI_API_KEY.startswith("your_"))

    return {
        "status": "online",
        "github_configured": has_github,
        "openai_configured": has_openai,
        "ai_engine": "OpenAI GPT-4o-mini" if has_openai else "Intelligent Heuristic AI Engine (Offline Safe)",
        "security_scanner": "Bandit v1.9.4",
        "bug_detector": "Pyflakes v4.0.3",
        "database": "In-Memory Session (Ephemeral)"
    }


# ------------------------------------------------------------------------------
# STEP 8: SERVE THE FRONTEND WEB PAGES
# ------------------------------------------------------------------------------
# This makes our website open automatically when someone visits http://127.0.0.1:8000 in their browser.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
