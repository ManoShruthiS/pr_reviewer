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

## 🚀 Quick Start Guide (How to Run on Any Laptop)

### Prerequisites:
- **Python 3.10+** installed on the computer ([python.org](https://www.python.org/downloads/)). *Make sure to check "Add Python to PATH" during installation.*

---

### Step 1: Clone or Download the Project
```bash
git clone https://github.com/ManoShruthiS/pr_reviewer.git
cd pr_reviewer
```
*(Or click **Code -> Download ZIP** on GitHub, and extract the folder).*

---

### Step 2: Install Dependencies (One-time only)
Open Command Prompt or Terminal inside the `pr_reviewer` folder and run:
```bash
pip install -r requirements.txt
```

---

### Step 3: Run the Application

#### ⚡ Option A (Easiest — 1-Click for Windows):
Simply double-click the **`run_project.bat`** file in the root directory.
> It will automatically start the server and open the web dashboard in your browser!

#### 💻 Option B (Command Line):
```bash
cd backend
python -m uvicorn main:app --reload
```
Then open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

### Step 4: Optional Configuration (`.env`)
The system works **100% out-of-the-box in free offline mode** without requiring any keys.
If you have personal API tokens for higher rate limits or cloud AI:
1. Create a file named `.env` inside the `backend/` folder:
```ini
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_key_here
```

## Team

- **Mano Shruthi S** — Core pipeline and GitHub fetch
- **Pratigsaa S** — Static analysis
- **Safrina S** — AI and explanation layer
- **Srivarshini V** — Dashboard and database

## Institution

Avinashilingam Institute for Home Science & Higher Education for Women, Coimbatore
