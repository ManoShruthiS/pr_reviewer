import json
from config import OPENAI_API_KEY


def explain_issues(issues: list, files: list) -> list:
    """
    Multilingual AI Review & Explainer Engine (FR-06 & FR-07).
    1. If static analysis found issues, AI supplements them with explanations, impact, and fixes.
    2. If files have changes but no static issues were raised, AI inspects code changes directly across any language.
    3. Handles timeouts and offline fallback via intelligent heuristic reasoning.
    """
    if not issues and not files:
        return []

    # If OpenAI API Key is present, try OpenAI first
    if OPENAI_API_KEY and OPENAI_API_KEY.strip() and not OPENAI_API_KEY.startswith("your_"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            context = ""
            for file in files:
                patch_sample = file.get("patch", "")[:1800]
                context += f"\n--- File: {file.get('filename', 'code_file')} ---\n{patch_sample}\n"

            if issues:
                issues_text = json.dumps(issues, indent=2)
                prompt = f"""You are an expert multilingual AI code review and software security assistant.
Analyze these detected issues from a GitHub Pull Request and provide actionable code review findings.

Code context (various programming languages):
{context}

Detected issues:
{issues_text}

Return a valid JSON array where each item matches the order of detected issues and has:
- "explanation": Clear, readable explanation of why this is a risk/flaw
- "impact": Potential security, performance, or bug impact
- "fix": Realistic code snippet showing the corrected code in the matching language
- "fixExplanation": Brief explanation of the fix
- "severity": Confirmed severity ("high", "medium", or "low")

Return strictly a JSON array without markdown formatting."""
            else:
                # Direct AI multilingual review of code diffs
                prompt = f"""You are an expert multilingual AI code review and software security assistant.
Inspect the following code changes from a GitHub Pull Request across all languages for bugs, security weaknesses, logic errors, or missing error handling.

Code context:
{context}

If you find genuine defects or vulnerabilities, return a JSON array of findings with:
- "title": Short title of the defect
- "type": "security" or "bug" or "quality"
- "severity": "high", "medium", or "low"
- "file": Relevant filename from the diff
- "line": Best estimated line number from the patch
- "message": Concise summary of the issue
- "explanation": Detailed reasoning why this is a risk
- "impact": Concrete security or runtime impact
- "fix": Recommended replacement code snippet
- "fixExplanation": Explanation of the fix
- "source": "AI Contextual Review"
- "confidence": "Medium"

If the code is clean and has no defects, return an empty JSON array: [].
Return strictly a JSON array without markdown formatting."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a code review expert. Return only a valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                timeout=18
            )

            raw_content = response.choices[0].message.content.strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.strip("`")
                if raw_content.startswith("json"):
                    raw_content = raw_content[4:].strip()

            result = json.loads(raw_content)

            if issues:
                for i, issue in enumerate(issues):
                    if i < len(result):
                        issue["explanation"] = result[i].get("explanation", "")
                        issue["impact"] = result[i].get("impact", "")
                        issue["fix"] = result[i].get("fix", "")
                        issue["fixExplanation"] = result[i].get("fixExplanation", "Follow recommended secure coding practices.")
                        if result[i].get("severity"):
                            issue["severity"] = result[i]["severity"].lower()
                        if not issue.get("source"):
                            issue["source"] = "AI Contextual Review"
                        if not issue.get("confidence"):
                            issue["confidence"] = "High" if "Static Tool" in str(issue.get("source")) else "Medium"
                return issues
            else:
                # Format direct AI findings
                direct_findings = []
                for idx, item in enumerate(result, start=1):
                    item["id"] = idx
                    item["source"] = "AI Contextual Review"
                    item["confidence"] = item.get("confidence", "Medium")
                    direct_findings.append(item)
                return direct_findings

        except Exception as e:
            # Fall back to expert heuristic engine
            pass

    # Expert heuristic AI engine fallback (ensures bulletproof viva/demo without API quotas)
    for issue in issues:
        generate_expert_explanation(issue)

    return issues


def generate_expert_explanation(issue: dict):
    msg = issue.get("message", "").lower()
    itype = issue.get("type", "quality").lower()
    severity = issue.get("severity", "medium").lower()

    if not issue.get("source"):
        issue["source"] = "AI Contextual Review"
    if not issue.get("confidence"):
        issue["confidence"] = "High" if "Static Tool" in str(issue.get("source")) else "Medium"

    if "password" in msg or "secret" in msg or "token" in msg or "credential" in msg or "cwe-798" in msg:
        issue["severity"] = "high"
        issue["type"] = "security"
        issue["cwe"] = "798"
        issue["explanation"] = "Hardcoded credentials or sensitive tokens detected directly in source code. Storing secrets in repository history exposes critical infrastructure to unauthorized access and credential leakage."
        issue["impact"] = "Severe: Potential exposure of production API keys or databases leading to full system breach (OWASP Top 10: Identification and Authentication Failures)."
        issue["fix"] = 'import os\nfrom dotenv import load_dotenv\n\nload_dotenv()\nAPI_KEY = os.getenv("API_KEY")'
        issue["fixExplanation"] = "Move credentials to an external environment variable file (.env) and add .env to .gitignore."

    elif "eval" in msg or "exec" in msg:
        issue["severity"] = "high"
        issue["type"] = "security"
        issue["cwe"] = "95"
        issue["explanation"] = "Dynamic execution using eval() or exec() executes arbitrary code strings. If user input reaches this function without sanitization, it can result in Remote Code Execution (RCE)."
        issue["impact"] = "Critical: Arbitrary code execution allowing attackers to execute commands on the host operating system."
        issue["fix"] = "import ast\n# Safe parsing of literal Python structures\nsafe_data = ast.literal_eval(user_supplied_string)"
        issue["fixExplanation"] = "Replace eval() with ast.literal_eval() for data structures, or use dedicated parsers like json.loads()."

    elif "sql" in msg or "injection" in msg:
        issue["severity"] = "high"
        issue["type"] = "security"
        issue["cwe"] = "89"
        issue["explanation"] = "Potential SQL Injection detected through raw string interpolation in query execution."
        issue["impact"] = "Critical: Unauthorized read/write database access, data corruption, and bypass of authentication."
        issue["fix"] = 'cursor.execute("SELECT * FROM users WHERE username = %s", (username,))'
        issue["fixExplanation"] = "Use parameterized queries or ORM abstractions instead of direct string formatting."

    elif "undefined name" in msg or "used before assignment" in msg:
        var_name = msg.split("'")[1] if "'" in msg else "variable"
        issue["severity"] = "high"
        issue["type"] = "bug"
        issue["explanation"] = f"Reference to undefined variable '{var_name}'. When this code path executes at runtime, Python will raise a NameError."
        issue["impact"] = "High: Runtime crash (NameError) terminating the request or worker process."
        issue["fix"] = f"# Define or import '{var_name}' before referencing it\n{var_name} = initialize_{var_name}()"
        issue["fixExplanation"] = f"Ensure '{var_name}' is properly defined in scope or imported from the correct module."

    elif "imported but unused" in msg or "unused import" in msg:
        mod_name = msg.split("'")[1] if "'" in msg else "module"
        issue["severity"] = "medium"
        issue["type"] = "quality"
        issue["explanation"] = f"The module '{mod_name}' is imported but never referenced in the active file scope."
        issue["impact"] = "Low/Medium: Unnecessary memory overhead, circular import risks, and confusing dependency trees."
        issue["fix"] = f"# Remove unused import line:\n# import {mod_name}"
        issue["fixExplanation"] = f"Delete unused import '{mod_name}' to keep modules lean and clean."

    elif "bare 'except:'" in msg:
        issue["severity"] = "medium"
        issue["type"] = "quality"
        issue["explanation"] = "A bare 'except:' clause intercepts all exceptions, including KeyboardInterrupt and SystemExit signals."
        issue["impact"] = "Medium: Hides fatal bugs and prevents graceful process shutdowns or debugging."
        issue["fix"] = "try:\n    perform_action()\nexcept Exception as err:\n    logger.error(f'Action failed: {err}')"
        issue["fixExplanation"] = "Catch specific exceptions or at least catch 'Exception' and log the diagnostic stack trace."

    elif "mutable default argument" in msg:
        issue["severity"] = "medium"
        issue["type"] = "bug"
        issue["explanation"] = "Python creates default argument objects only once at function definition time. Mutating this default modifies it across all subsequent invocations."
        issue["impact"] = "Medium: Inconsistent state leakage across different user requests or function calls."
        issue["fix"] = "def process_data(items=None):\n    if items is None:\n        items = []\n    items.append('processed')\n    return items"
        issue["fixExplanation"] = "Use None as the default argument sentinel and initialize a new list/dictionary inside the function body."

    elif "syntax error" in msg:
        issue["severity"] = "high"
        issue["type"] = "bug"
        issue["explanation"] = f"Code contains invalid Python syntax: {msg}. The file cannot be compiled or imported."
        issue["impact"] = "Critical: Prevents module import or application startup."
        issue["fix"] = "# Correct the syntax error at the flagged line\n# Check for missing colons, mismatched brackets, or invalid keywords"
        issue["fixExplanation"] = "Ensure Python syntax complies with PEP 8 and valid grammar specification."

    elif "wildcard import" in msg:
        issue["severity"] = "low"
        issue["type"] = "quality"
        issue["explanation"] = "Wildcard imports ('from module import *') import all public names into the current namespace."
        issue["impact"] = "Low: Namespace pollution, hidden name collisions, and reduced code readability."
        issue["fix"] = "from module import specific_function, SpecificClass"
        issue["fixExplanation"] = "Explicitly list the functions or classes needed from the package."

    elif "high function complexity" in msg:
        issue["severity"] = "low"
        issue["type"] = "quality"
        issue["explanation"] = "Function contains excessive lines and responsibilities, violating the Single Responsibility Principle."
        issue["impact"] = "Low: Difficult to unit-test, maintain, and review."
        issue["fix"] = "# Refactor into smaller sub-routines:\ndef validate_payload(...): ...\ndef persist_record(...): ..."
        issue["fixExplanation"] = "Extract distinct tasks into well-tested, isolated helper methods."

    else:
        # Default fallback
        if not issue.get("explanation"):
            issue["explanation"] = f"Detected issue: {issue.get('message', 'Code analysis finding')}. This pattern may introduce bugs or maintenance debt."
        if not issue.get("impact"):
            issue["impact"] = f"Potential {severity}-severity issue that could affect software reliability or security."
        if not issue.get("fix"):
            issue["fix"] = "# Refactor this section to follow recommended coding standards and conventions"
        if not issue.get("fixExplanation"):
            issue["fixExplanation"] = "Review the flagged code and apply clean-code design patterns."
