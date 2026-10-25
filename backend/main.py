import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from fetcher import fetch_pr_diff
from analyzer import analyze_files
from ai_explainer import explain_issues
from risk_scorer import calculate_risk_score
from database import init_db, save_review, get_all_reviews, get_review_by_id
from config import GITHUB_TOKEN, OPENAI_API_KEY
from language_detector import analyze_pr_coverage

app = FastAPI(
    title="AI-Powered Intelligent Code Review and Risk Analysis System",
    description="Backend API for automated GitHub PR analysis, static security/bug scanning, and AI explanations."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Resolve frontend path
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class ReviewRequest(BaseModel):
    pr_url: str


@app.post("/review")
def review_pr(request: ReviewRequest):
    pr_url = request.pr_url.strip()
    if not pr_url:
        raise HTTPException(status_code=400, detail="Pull request URL cannot be empty.")

    try:
        # 1. Fetch PR details and changed files
        pr_data = fetch_pr_diff(pr_url)
        files = pr_data.get("files", [])

        # 2. Analyze PR coverage & detected languages (FR-04 & FR-12)
        coverage_data = analyze_pr_coverage(files)

        # 3. Run static analysis (Pyflakes bugs, Bandit security, AST quality, regex patterns)
        raw_issues = analyze_files(files)

        # 4. Enhance with AI explanations & recommended code fixes (FR-06 & FR-07)
        issues = explain_issues(raw_issues, files)

        # 5. Calculate Risk Score (0-100)
        risk_score = calculate_risk_score(issues)

        # 6. Save to SQLite database
        review_id = save_review(
            pr_url=pr_url,
            pr_title=pr_data.get("title", "GitHub Pull Request"),
            risk_score=risk_score,
            issues_json=json.dumps(issues)
        )

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
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


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


# Mount frontend static directory at root AFTER all API routes
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
