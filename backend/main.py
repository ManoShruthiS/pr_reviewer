import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fetcher import fetch_pr_diff
from analyzer import analyze_files
from ai_explainer import explain_issues
from risk_scorer import calculate_risk_score
from database import init_db, save_review

app = FastAPI(title="AI Code Review API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class ReviewRequest(BaseModel):
    pr_url: str


@app.post("/review")
def review_pr(request: ReviewRequest):
    pr_data = fetch_pr_diff(request.pr_url)
    issues = analyze_files(pr_data["files"])
    issues = explain_issues(issues, pr_data["files"])
    risk_score = calculate_risk_score(issues)

    save_review(
        pr_url=request.pr_url,
        pr_title=pr_data["title"],
        risk_score=risk_score,
        issues_json=json.dumps(issues)
    )

    return {
        "riskScore": risk_score,
        "prTitle": pr_data["title"],
        "author": pr_data["author"],
        "issues": issues
    }


@app.get("/history")
def get_history():
    from database import get_all_reviews
    reviews = get_all_reviews()
    return [
        {
            "id": r.id,
            "pr_url": r.pr_url,
            "pr_title": r.pr_title,
            "risk_score": r.risk_score,
            "created_at": r.created_at.isoformat()
        }
        for r in reviews
    ]


@app.get("/")
def root():
    return {"status": "AI Code Review API is running"}
