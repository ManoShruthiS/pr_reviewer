# ==============================================================================
# FILE: analyzer.py
# PURPOSE: The core code scanner that hunts for security holes, bugs, and bad code habits.
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like an automated building inspector or medical diagnostic test:
# 1. Tool #1 (Pyflakes): Checks if the code has broken sentences, misspelled variables,
#    or tools that were ordered but never used.
# 2. Tool #2 (Bandit): An official cybersecurity auditor that checks for dangerous
#    hacker vulnerabilities (like weak passwords, dangerous commands, or unsafe inputs).
# 3. Tool #3 (AST Quality Linter): Examines the structure of the code (like an X-ray)
#    to detect messy shortcuts (e.g. ignoring errors, overly long functions).
# 4. Tool #4 (Multilingual Scanner): Checks other languages like JavaScript, Java, Go,
#    and C++ for common security mistakes like Cross-Site Scripting (XSS) and SQL Injection!
# ==============================================================================

# ------------------------------------------------------------------------------
# STEP 1: IMPORT PYTHON TOOLS
# ------------------------------------------------------------------------------
import ast          # "Abstract Syntax Tree" - turns code into an X-ray tree structure to inspect it
import io           # Helps handle text streams in memory
import re           # "Regular Expressions" - searches for specific text patterns (like passwords)
import subprocess   # Allows Python to run command-line tools in the background
import tempfile     # Creates safe, temporary scratchpad files that disappear after use
import os           # Talks to the computer's file system
import sys          # Gives access to the currently running Python interpreter
from pathlib import Path


# ------------------------------------------------------------------------------
# SCANNER #1: PYFLAKES (SYNTAX AND LOGIC ERROR DETECTOR)
# ------------------------------------------------------------------------------
# Pyflakes checks Python code without running it. It instantly finds things like:
# - Undefined variables (e.g. using 'x' when 'x' was never created)
# - Unused imports (e.g. importing math but never using it)
# - Broken grammar / syntax errors
def run_pyflakes(code: str, filename: str, is_fragment: bool = False) -> list:
    issues = []
    try:
        # Check if Python can parse the text code into a valid syntax tree
        tree = ast.parse(code)
        import pyflakes.api
        import pyflakes.reporter

        # A custom collector class that listens to Pyflakes and saves its warnings into our list
        class Collector:
            def __init__(self):
                self.messages = []

            def unexpectedError(self, filename, error):
                pass  # Ignore internal Pyflakes errors

            # Triggered if there is a severe typo or broken grammar in the code
            def syntaxError(self, filename, message, lineno, offset, text):
                # If we are inspecting only a snippet (diff hunk), ignore partial indentation warnings
                if is_fragment and ("indent" in str(message).lower() or "unexpected eof" in str(message).lower()):
                    return
                self.messages.append({
                    "id": f"bug_{len(self.messages)+1}",
                    "type": "bug",
                    "severity": "high",
                    "file": filename,
                    "line": lineno or 1,
                    "message": f"Syntax error: {message}",
                    "source": "Pyflakes Syntax"
                })

            # Triggered for logical warnings (like undefined variables or unused imports)
            def flake(self, message):
                msg_str = str(message)
                clean_msg = msg_str.split(": ", 1)[-1] if ": " in msg_str else msg_str
                msg_lower = clean_msg.lower()

                # Case A: A variable was used before being defined (This is a dangerous bug!)
                if "undefined name" in msg_lower or "used before assignment" in msg_lower:
                    itype = "bug"
                    severity = "high"
                    source = "Pyflakes F821"
                # Case B: An import was loaded but never used (Just a harmless code smell)
                elif "imported but unused" in msg_lower or "redefinition of unused" in msg_lower:
                    itype = "quality"
                    severity = "low"
                    source = "Pyflakes F401"
                # Case C: Any other general code notice
                else:
                    itype = "quality"
                    severity = "low"
                    source = "Pyflakes"

                self.messages.append({
                    "id": f"issue_{len(self.messages)+1}",
                    "type": itype,
                    "severity": severity,
                    "file": filename,
                    "line": getattr(message, "lineno", 1),
                    "message": clean_msg,
                    "source": source
                })

        # Run Pyflakes check on the code using our collector
        reporter = Collector()
        pyflakes.api.check(code, filename, reporter)
        issues.extend(reporter.messages)

    # If Python cannot read the code at all due to broken grammar, catch the SyntaxError
    except SyntaxError as e:
        if not (is_fragment and ("indent" in str(e.msg).lower() or "unexpected eof" in str(e.msg).lower())):
            issues.append({
                "id": f"bug_{len(issues)+1}",
                "type": "bug",
                "severity": "high",
                "file": filename,
                "line": e.lineno or 1,
                "message": f"Syntax error: {e.msg}",
                "source": "Pyflakes Syntax"
            })
    except Exception:
        pass

    return issues


# ------------------------------------------------------------------------------
# SCANNER #2: BANDIT (SECURITY VULNERABILITY AUDITOR)
# ------------------------------------------------------------------------------
# Bandit is the industry standard security scanner for Python.
# It looks for security flaws like hardcoded passwords, unsafe shell executions,
# and insecure cryptographic algorithms.
def run_bandit(code: str, filename: str) -> list:
    issues = []
    # Write the code into a temporary file on disk so the Bandit CLI tool can read it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        temp_path = f.name

    try:
        # Run Bandit quietly (-q) and request output in JSON format (-f json)
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-q", temp_path],
            capture_output=True, text=True
        )
        # Parse Bandit's JSON output
        if result.stdout:
            import json
            data = json.loads(result.stdout)
            for item in data.get("results", []):
                severity = item.get("issue_severity", "LOW").lower()
                issues.append({
                    "id": f"sec_{len(issues)+1}",
                    "type": "security",
                    "severity": severity,
                    "file": filename,
                    "line": item.get("line_number", 1),
                    "message": item.get("issue_text", "Security vulnerability detected"),
                    "cwe": item.get("issue_cwe", {}).get("id", ""),
                    "test_id": item.get("test_id", ""),
                    "source": f"Bandit {item.get('test_id', '')}".strip() or "Bandit Security"
                })
    except Exception:
        pass
    finally:
        # Always delete the temporary scratchpad file when done
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    return issues


# ------------------------------------------------------------------------------
# SCANNER #3: AST QUALITY LINTER (STRUCTURAL CODE HEALTH)
# ------------------------------------------------------------------------------
# AST looks at the tree structure of the code to detect risky programming habits:
# 1. Silencing errors with empty "pass" statements
# 2. Dangerous mutable default arguments (e.g. def add_item(list=[]))
# 3. Super long functions that are hard to maintain (> 35 lines)
# 4. Wildcard imports (e.g. from math import *)
def run_ast_quality_checks(code: str, filename: str) -> list:
    issues = []
    try:
        tree = ast.parse(code)

        # Walk through every structural node in the Python code
        for node in ast.walk(tree):
            # Check #1: Catch-all 'except:' or empty 'pass' inside an except block
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        "id": f"quality_{len(issues)+1}",
                        "type": "quality",
                        "severity": "medium",
                        "file": filename,
                        "line": getattr(node, "lineno", 1),
                        "message": "Bare 'except:' clause caught all exceptions including system exits",
                        "source": "AST Linter"
                    })
                elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append({
                        "id": f"quality_{len(issues)+1}",
                        "type": "quality",
                        "severity": "low",
                        "file": filename,
                        "line": getattr(node, "lineno", 1),
                        "message": "Silenced exception: 'except' block with only 'pass' statement",
                        "source": "AST Linter"
                    })

            # Check #2: Function definitions with risky defaults or high complexity
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Detect mutable default argument like def foo(items=[]):
                for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "id": f"quality_{len(issues)+1}",
                            "type": "bug",
                            "severity": "medium",
                            "file": filename,
                            "line": getattr(node, "lineno", 1),
                            "message": f"Mutable default argument in '{node.name}()' leads to unexpected state retention",
                            "source": "AST Linter"
                        })

                # Check if the function is too long (> 35 lines)
                end_lineno = getattr(node, "end_lineno", None)
                if end_lineno and (end_lineno - node.lineno) > 35:
                    issues.append({
                        "id": f"quality_{len(issues)+1}",
                        "type": "quality",
                        "severity": "low",
                        "file": filename,
                        "line": node.lineno,
                        "message": f"High function complexity: '{node.name}()' exceeds 35 lines; consider refactoring",
                        "source": "AST Linter"
                    })

            # Check #3: Wildcard imports (like: from math import *)
            if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
                issues.append({
                    "id": f"quality_{len(issues)+1}",
                    "type": "quality",
                    "severity": "low",
                    "file": filename,
                    "line": getattr(node, "lineno", 1),
                    "message": f"Wildcard import 'from {node.module} import *' pollutes the global namespace",
                    "source": "AST Linter"
                })

    except Exception:
        pass
    return issues


# ------------------------------------------------------------------------------
# SCANNER #4: MULTILINGUAL REGEX RULES (JS, TS, JAVA, GO, C++, PHP, HTML)
# ------------------------------------------------------------------------------
# Scans non-Python files using high-precision regex pattern rules:
# - Hardcoded secrets & passwords
# - Dangerous eval() executions
# - Cross-Site Scripting (XSS via innerHTML)
# - SQL Injection (query string concatenation)
# - Command Injections
# - Leftover debugging print statements
def run_multilingual_regex_patterns(code: str, filename: str) -> list:
    issues = []
    lines = code.split("\n")
    suffix = Path(filename).suffix.lower()

    # Skip Python files because Python is already scanned by Bandit and AST above
    if suffix in [".py", ".pyw"]:
        return issues

    # Inspect the code line by line
    for line_idx, line in enumerate(lines, start=1):
        clean_line = line.strip()

        # 1. Hardcoded API secrets or passwords (e.g. api_key = "abc1234567890123")
        if re.search(r'(?:api_key|secret|password|auth_token|jwt_secret)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']', clean_line, re.IGNORECASE):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Hardcoded secret or credential token detected in source code",
                "cwe": "798",
                "source": "Secret Scanner (CWE-798)"
            })

        # 2. Unsafe dynamic eval() execution (in JS, TS, or PHP)
        if suffix in [".js", ".jsx", ".ts", ".tsx", ".php"] and re.search(r'\b(?:eval|new\s+Function)\s*\(', clean_line):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Unsafe dynamic code execution: arbitrary expression evaluation",
                "cwe": "95",
                "source": "Security Linter (CWE-95)"
            })

        # 3. Cross-Site Scripting (DOM XSS via unescaped innerHTML or document.write)
        if suffix in [".js", ".jsx", ".ts", ".tsx", ".html"] and re.search(r'\.(?:innerHTML|outerHTML)\s*=\s*[^"\'`]|document\.write\s*\(', clean_line):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Potential Cross-Site Scripting (DOM XSS): unescaped assignment to innerHTML/document.write",
                "cwe": "79",
                "source": "DOM Security (CWE-79)"
            })

        # 4. SQL Injection via direct string concatenation ("SELECT * FROM users WHERE id=" + id)
        if re.search(r'(?:select\s+.+\s+from|insert\s+into|delete\s+from|update\s+.+\s+set)\s*.*\+\s*[A-Za-z0-9_]+', clean_line, re.IGNORECASE):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Potential SQL Injection: direct string concatenation in SQL query",
                "cwe": "89",
                "source": "SQLi Auditor (CWE-89)"
            })

        # 5. OS Command Injection (unsanitized inputs passed to system terminal execution)
        if re.search(r'(?:child_process\.(?:exec|execSync)|Runtime\.getRuntime\(\)\.exec|system\(|popen\(|exec\.Command\()\s*\(?[^)]*\+', clean_line):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Potential OS Command Injection: unsanitized command string passed to system process",
                "cwe": "78",
                "source": "Command Injection Auditor"
            })

        # 6. Leftover debug statements left in production code (e.g. console.log, System.out.println)
        if (suffix in [".js", ".jsx", ".ts", ".tsx"] and re.search(r'\bconsole\.(?:log|debug|warn)\s*\(', clean_line)) or \
           (suffix in [".java", ".kt"] and re.search(r'\bSystem\.out\.print(?:ln)?\s*\(', clean_line)) or \
           (suffix in [".php"] and re.search(r'\b(?:var_dump|print_r)\s*\(', clean_line)) or \
           (suffix in [".go"] and re.search(r'\bfmt\.Print(?:ln|f)?\s*\(', clean_line)):
            issues.append({
                "id": f"qual_{len(issues)+1}",
                "type": "quality",
                "severity": "low",
                "file": filename,
                "line": line_idx,
                "message": f"Leftover debug statement '{clean_line[:35]}...' should be removed in production code",
                "source": "Quality Linter"
            })

    return issues


# ------------------------------------------------------------------------------
# STEP 5: MASTER COORDINATOR FUNCTION (analyze_files)
# ------------------------------------------------------------------------------
# Takes all the files downloaded from GitHub, chooses the right tools for each file,
# collects all the discovered problems, and gives each problem a clean ID number (1, 2, 3...)
def analyze_files(files: list) -> list:
    all_issues = []

    for file in files:
        filename = file.get("filename", "unknown.py")
        patch = file.get("patch", "")

        # Prefer full authentic source code from the PR commit
        content = file.get("content", "")
        if content and content.strip():
            code = content
            is_fragment = False
        else:
            # If full file is unavailable, use the added (+) lines from the git patch
            code = extract_added_code(patch)
            is_fragment = True

        # If the file has no code content, skip it
        if not code or not code.strip():
            continue

        suffix = Path(filename).suffix.lower()

        # Route 1: Python Files -> Run Pyflakes, Bandit, and AST Quality checks
        if suffix in [".py", ".pyw"]:
            pyflakes_issues = run_pyflakes(code, filename, is_fragment=is_fragment)
            bandit_issues = run_bandit(code, filename)
            quality_issues = run_ast_quality_checks(code, filename)
            all_issues.extend(pyflakes_issues)
            all_issues.extend(bandit_issues)
            all_issues.extend(quality_issues)
        # Route 2: Multilingual Files (JS, TS, Java, Go, etc.) -> Run regex pattern rules
        else:
            pattern_issues = run_multilingual_regex_patterns(code, filename)
            all_issues.extend(pattern_issues)

    # Assign clean sequential integer IDs (1, 2, 3, 4...) to every issue found
    for idx, issue in enumerate(all_issues, start=1):
        issue["id"] = idx

    return all_issues


# ------------------------------------------------------------------------------
# HELPER: EXTRACT ADDED LINES FROM GIT PATCH
# ------------------------------------------------------------------------------
# Git diffs mark newly added lines with a '+' symbol.
# This helper filters out those newly added lines so we only scan the new code.
def extract_added_code(patch: str) -> str:
    lines = []
    for line in patch.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])  # Strip off the leading '+' symbol
    return "\n".join(lines)
