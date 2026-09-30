# AI-Powered Intelligent Code Review and Risk Analysis for GitHub Pull Requests

A web-based intelligent code review system that analyzes GitHub Pull Requests, identifies bugs, security vulnerabilities, and code-quality problems, assesses severity and risk, explains findings, and suggests fixes before merge.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **GitHub Integration:** PyGithub
- **Bug Detection:** Pyflakes
- **Security Scanning:** Bandit
- **AI / Explanations:** Contextual LLM API & Heuristic Explainer
- **Multi-Language Detection:** Extensible Language Registry & Manifest (FR-04, FR-12)
- **Risk Scoring:** Weighted Formula (0–100 scale)
- **Database:** SQLite + SQLAlchemy
- **Dashboard:** Modern Vanilla HTML5 / CSS3 / JavaScript (GitHub Slate Theme)

## Project Structure

```
pr_reviewer/
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── logo.png
├── backend/
│   ├── main.py
│   ├── fetcher.py
│   ├── analyzer.py
│   ├── ai_explainer.py
│   ├── language_detector.py
│   ├── risk_scorer.py
│   └── database.py
├── requirements.txt
├── run_project.bat
├── .gitignore
└── README.md
```

## How It Works

1. User enters a GitHub Pull Request URL
2. System fetches changed files and diffs via PyGithub
3. Static analysis runs (Pyflakes for bugs, Bandit for security)
4. OpenAI LLM generates explanations, severity levels, and fix suggestions
5. Risk score (0–100) is calculated
6. Results displayed on a web dashboard

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:
```
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_key
```

Run the backend:
```bash
cd backend
uvicorn main:app --reload
```

Open `frontend/index.html` in a browser.

## Team

- **Mano Shruthi S** — Core pipeline and GitHub fetch
- **Pratigsaa S** — Static analysis
- **Safrina S** — AI and explanation layer
- **Srivarshini V** — Dashboard and database

## Institution

Avinashilingam Institute for Home Science & Higher Education for Women, Coimbatore
