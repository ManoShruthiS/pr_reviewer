# 🏛️ System Architecture & Engineering Specifications
### *PR-Doc: AI-Powered Intelligent Code Review and Risk Analysis System*

---

## 1. System Overview & Problem Formulation
In modern software engineering, peer code review via **Pull Requests (PRs)** is a critical quality gate. However, manual human code review faces significant bottlenecks:
- Senior engineers spend up to 20% of their development time reviewing diffs.
- Critical vulnerabilities (CWE-798 hardcoded credentials, CWE-89 SQL injection, CWE-79 DOM XSS) frequently escape into production.
- Turnaround time for PR approval slows release velocity.

**PR-Doc** addresses this by providing an **automated, deterministic static analysis and intelligent risk scoring pipeline**.
Within seconds of submitting a GitHub Pull Request URL, the platform:
1. Ingests unified diffs and authentic source content via GitHub API.
2. Identifies changed languages and computes PR coverage percentage.
3. Concurrently executes static security linters (Bandit), syntax/bug detectors (Pyflakes), and structural AST auditors.
4. Generates contextual explanations, security impacts, and copy-paste remediation diffs.
5. Computes a defensible, mathematical **Risk Score (0–100)** to assist merge decisions.
6. Renders a single-page Executive Landscape Audit Report ready for stakeholder export.

---

## 2. High-Level Architecture & Data Flow

```
                                +-----------------------------+
                                |      Web Client (UI)        |
                                |  HTML5 / CSS3 / Vanilla JS  |
                                +--------------+--------------+
                                               |
                                     HTTP POST | /review
                                               v
                                +--------------+--------------+
                                |   FastAPI Gateway (main.py) |
                                +--------------+--------------+
                                               |
            +-------------------+--------------+-------------------+
            |                                  |                   |
            v                                  v                   v
+-----------+-----------+          +-----------+-----------+  +----+------------------+
|   GitHub Diff Fetcher |          |   Language Detector   |  | In-Memory SQLite DB   |
|      (fetcher.py)     |          |(language_detector.py) |  |    (database.py)      |
+-----------+-----------+          +-----------+-----------+  +-----------------------+
            |
            v
+-----------+------------------------------------------------------+
|                       Static Analysis Engine                     |
|                           (analyzer.py)                          |
|                                                                  |
|   [Pyflakes v4.0]     [Bandit v1.9.4]    [AST Linter]    [Regex] |
|   Syntax & Logic      Security CWEs      Structure       Multi-  |
|   Undefined Vars      Secrets / Eval     Complexity      lingual |
+----------------------------------+-------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------+
|                       AI & Heuristics Explainer                  |
|                           (ai_explainer.py)                      |
|       - Risk impact explanations                                 |
|       - Deterministic copy-paste code patches                    |
|       - Hybrid: OpenAI GPT-4o-mini / Offline Heuristics Engine   |
+----------------------------------+-------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------+
|                       Risk Scorer Engine                         |
|                          (risk_scorer.py)                        |
|   Formula: Score = Sum(Weighted Penalties), Capped at 100       |
+------------------------------------------------------------------+
```

---

## 3. End-to-End Processing Pipeline (Step-by-Step)

### **Phase 1: Ingestion & URL Parsing (`fetcher.py`)**
- The user inputs a GitHub Pull Request URL (e.g. `https://github.com/owner/repo/pull/123`).
- The parser extracts repository owner, repository name, and PR number.
- PyGithub establishes a connection (authenticated via `GITHUB_TOKEN` for up to 5,000 req/hr, or unauthenticated up to 60 req/hr).
- Full source files at the PR head commit are retrieved to eliminate git diff indentation artifacts.

### **Phase 2: Multilingual Language Detection & Coverage (`language_detector.py`)**
- Files are mapped against an extensive language capability dictionary (`.py`, `.js`, `.ts`, `.java`, `.go`, `.cpp`, `.html`, `.css`, etc.).
- Machine-generated lockfiles (`package-lock.json`, `poetry.lock`, minified assets) are excluded to eliminate false positives.
- A transparent coverage metric is computed: `Coverage % = (Analyzed Files / Total Files) * 100`.

### **Phase 3: Deep Static Security & Bug Scanning (`analyzer.py`)**
Four specialized inspection engines run across all submitted files:
1. **Pyflakes:** AST-level compiler analysis detecting undefined variables (F821), used-before-assignment bugs, and unused imports (F401).
2. **Bandit:** Official Python security auditor mapping vulnerabilities directly to Common Weakness Enumeration standards (e.g., CWE-798 hardcoded credentials, CWE-95 dynamic code evaluation).
3. **AST Structural Linter:** Inspects code syntax trees for anti-patterns: bare `except:` clauses, silenced errors with `pass`, mutable default arguments (`def foo(items=[])`), and oversized routines exceeding 35 lines.
4. **Multilingual Regex Scanner:** Analyzes non-Python languages (JavaScript, TypeScript, Java, Go, C++, PHP) for Cross-Site Scripting (`innerHTML`), SQL concatenation, and unhandled system commands.

### **Phase 4: Contextual Remediation & Explanation (`ai_explainer.py`)**
- Each raw finding is enriched with:
  - **Technical Explanation:** Clear explanation of why the detected pattern constitutes a defect or vulnerability.
  - **Risk Impact:** Potential runtime crash, data breach, or maintainability degradation.
  - **Recommended Patch:** Production-ready code replacement.
- Built-in **Expert Heuristic Engine** guarantees 100% deterministic operation offline without requiring third-party API quotas.

### **Phase 5: Mathematical Risk Score Calculation (`risk_scorer.py`)**
Risk is evaluated using a weighted penalty accumulation formula:
$$\text{Risk Score} = \min\left(100, \sum \text{Weights}\right)$$

| Finding Category | Severity Level | Penalty Weight | Rationale |
| :--- | :--- | :---: | :--- |
| **Security Vulnerability** | Critical / High | **+35 pts** | Threatens database or system integrity (CWE-89, CWE-798) |
| **Security Vulnerability** | Medium | **+20 pts** | Moderate risk exposure |
| **Security Vulnerability** | Low | **+10 pts** | Minor security advisory |
| **Functional Bug** | Critical / High | **+25 pts** | Runtime crash / fatal exception |
| **Functional Bug** | Medium | **+15 pts** | Unexpected state retention or variable logic issue |
| **Functional Bug** | Low | **+6 pts** | Minor logic defect |
| **Code Quality / Smell** | High / Medium | **+4 to +8 pts**| Maintainability debt |
| **Code Quality / Smell** | Low | **+2 pts** | Cleanliness / PEP 8 compliance |

#### Risk Classifications:
- **0 – 25 (Low Risk):** Safe to merge with standard peer approval. 🟢
- **26 – 50 (Medium Risk):** Moderate bug/maintainability concerns. Resolve prior to deployment. 🟡
- **51 – 75 (High Risk):** Critical findings detected. Must resolve before merge. 🔴
- **76 – 100 (Critical Risk):** Block merge immediately! Severe security flaws detected. ⛔

### **Phase 6: In-Memory Persistence & Client Presentation (`database.py` & `script.js`)**
- Review records are stored in an ephemeral SQLite database (`sqlite:///:memory:`).
- Web frontend dynamically updates the animated risk gauge, issue cards, and single-page Executive Landscape Audit Report.

---

## 4. Technical Defense & Architecture Questions (Q&A)

### Q1: What is the core problem solved by PR-Doc?
> **Answer:** PR-Doc automates the code review bottleneck in CI/CD pipelines. It statically analyzes Pull Requests across security, functionality, and code quality dimensions, providing automated risk scoring and deterministic remediation patches before code reaches production branches.

### Q2: What is the architecture of the system?
> **Answer:** The system follows a decoupled client-server architecture. The frontend is built using standard HTML5/CSS3 and Vanilla JavaScript. The backend is built with FastAPI in Python, orchestrating GitHub API ingestion, Pyflakes, Bandit, Python AST parsing, an expert heuristic explanation engine, and SQLite session storage.

### Q3: Why combine static analysis tools (Bandit, Pyflakes) with AI heuristics?
> **Answer:** Pure AI/LLM reviews are probabilistic and can hallucinate or miss subtle syntax defects, while pure static linters produce dry warning codes without explanatory context or actionable diffs. Combining deterministic static analysis (Bandit/Pyflakes) with an intelligent explainer engine ensures 100% reproducible, verifiable vulnerability detection backed by human-readable explanations and fixes.

### Q4: How is the Risk Score calculated?
> **Answer:** It uses a transparent, defensible weighted penalty model capped at 100. High-severity security vulnerabilities contribute +35 points, crashing bugs contribute +25 points, and quality smells contribute +2 to +8 points. This reflects real-world software engineering priorities where security and reliability take precedence over formatting.

### Q5: What security vulnerabilities are detected?
> **Answer:** The system identifies OWASP Top 10 and Common Weakness Enumeration (CWE) flaws, including:
> - **CWE-798:** Hardcoded credentials and tokens in source code.
> - **CWE-89:** SQL Injection via raw query concatenation.
> - **CWE-95:** Arbitrary code execution via dynamic `eval()` or `exec()`.
> - **CWE-79:** Cross-Site Scripting (DOM XSS) via unescaped DOM sinks (`innerHTML`).
> - **CWE-78:** OS Command Injection in system process invocations.

### Q6: How does the system handle multi-language repositories?
> **Answer:** `language_detector.py` scans PR file extensions and maps each file to its corresponding language family. Python files undergo AST and Bandit analysis, while multilingual files (JS, TS, Java, Go, C++, PHP) undergo precision regex-based pattern analysis. A transparent coverage percentage is displayed to the user.

### Q7: Why use an In-Memory SQLite database?
> **Answer:** In-memory storage (`sqlite:///:memory:`) keeps session review history accessible within the application while ensuring privacy, zero disk clutter, and complete isolation between server restarts.

### Q8: How is the executive audit report generated?
> **Answer:** The application includes a dedicated single-page print stylesheet (`@media print`) paired with an `#executiveReportSheet` DOM component. When users click "Export PDF / Print", the browser renders a print-optimized, landscape audit summary fitting onto a single sheet of paper.

---

## 5. Module Responsibilities Matrix

| Module | Primary Responsibility | Key Libraries |
| :--- | :--- | :--- |
| `backend/main.py` | API routing, CORS management, request validation, and pipeline orchestration | `FastAPI`, `Pydantic` |
| `backend/fetcher.py` | GitHub PR URL parsing, diff ingestion, commit file content retrieval | `PyGithub` |
| `backend/analyzer.py` | Static code analysis, vulnerability detection, syntax checking | `bandit`, `pyflakes`, `ast`, `re` |
| `backend/ai_explainer.py` | Defect explanation, impact assessment, and code patch synthesis | `openai` (optional), Heuristic Engine |
| `backend/risk_scorer.py` | Mathematical penalty accumulation and risk classification | Python standard library |
| `backend/language_detector.py`| File extension identification, lockfile filtering, coverage computation | `pathlib` |
| `backend/database.py` | Ephemeral session persistence for audit history | `SQLAlchemy`, `sqlite3` |
| `backend/config.py` | Environment variable extraction and secret management | `python-dotenv` |
| `frontend/index.html` | Semantic markup, audit dashboard structure, printable report template | HTML5 |
| `frontend/style.css` | Design system, dark mode tokens, risk badges, `@media print` layout | CSS3 Vanilla |
| `frontend/script.js` | UI state machine, API fetch requests, score counter animation, report builder| Vanilla JavaScript |
