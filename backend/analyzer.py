import ast
import io
import re
import subprocess
import tempfile
import os
import sys
from pathlib import Path


def run_pyflakes(code: str, filename: str) -> list:
    issues = []
    try:
        tree = ast.parse(code)
        import pyflakes.api
        import pyflakes.reporter

        class Collector:
            def __init__(self):
                self.messages = []

            def unexpectedError(self, filename, error):
                pass

            def syntaxError(self, filename, message, lineno, offset, text):
                self.messages.append({
                    "id": f"bug_{len(self.messages)+1}",
                    "type": "bug",
                    "severity": "high",
                    "file": filename,
                    "line": lineno or 1,
                    "message": f"Syntax error: {message}",
                    "source": "Static Tool (Pyflakes)",
                    "confidence": "High"
                })

            def flake(self, message):
                severity = "low"
                msg_str = str(message)
                clean_msg = msg_str.split(": ", 1)[-1] if ": " in msg_str else msg_str
                if "undefined name" in clean_msg.lower() or "used before assignment" in clean_msg.lower():
                    severity = "high"
                elif "imported but unused" in clean_msg.lower():
                    severity = "medium"

                self.messages.append({
                    "id": f"bug_{len(self.messages)+1}",
                    "type": "bug",
                    "severity": severity,
                    "file": filename,
                    "line": getattr(message, "lineno", 1),
                    "message": clean_msg,
                    "source": "Static Tool (Pyflakes)",
                    "confidence": "High"
                })

        reporter = Collector()
        pyflakes.api.check(code, filename, reporter)
        issues.extend(reporter.messages)
    except SyntaxError as e:
        issues.append({
            "id": f"bug_{len(issues)+1}",
            "type": "bug",
            "severity": "high",
            "file": filename,
            "line": e.lineno or 1,
            "message": f"Syntax error: {e.msg}",
            "source": "Static Tool (Pyflakes)",
            "confidence": "High"
        })
    except Exception:
        pass
    return issues


def run_bandit(code: str, filename: str) -> list:
    issues = []
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        temp_path = f.name

    try:
        # Run bandit using current python interpreter to avoid PATH lookup issues
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-q", temp_path],
            capture_output=True, text=True
        )
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
                    "source": "Static Tool (Bandit)",
                    "confidence": "High"
                })
    except Exception:
        pass
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    return issues


def run_ast_quality_checks(code: str, filename: str) -> list:
    """AST checks for code quality and performance patterns (PPT objectives)"""
    issues = []
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            # 1. Bare except or pass in except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        "id": f"quality_{len(issues)+1}",
                        "type": "quality",
                        "severity": "medium",
                        "file": filename,
                        "line": getattr(node, "lineno", 1),
                        "message": "Bare 'except:' clause caught all exceptions including system exits",
                        "source": "Static Tool (AST Analysis)",
                        "confidence": "High"
                    })
                elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append({
                        "id": f"quality_{len(issues)+1}",
                        "type": "quality",
                        "severity": "low",
                        "file": filename,
                        "line": getattr(node, "lineno", 1),
                        "message": "Silenced exception: 'except' block with only 'pass' statement",
                        "source": "Static Tool (AST Analysis)",
                        "confidence": "High"
                    })

            # 2. Mutable default argument in function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "id": f"quality_{len(issues)+1}",
                            "type": "bug",
                            "severity": "medium",
                            "file": filename,
                            "line": getattr(node, "lineno", 1),
                            "message": f"Mutable default argument in '{node.name}()' leads to unexpected state retention",
                            "source": "Static Tool (AST Analysis)",
                            "confidence": "High"
                        })
                
                # Check for overly complex or long functions (> 35 lines)
                end_lineno = getattr(node, "end_lineno", None)
                if end_lineno and (end_lineno - node.lineno) > 35:
                    issues.append({
                        "id": f"quality_{len(issues)+1}",
                        "type": "quality",
                        "severity": "low",
                        "file": filename,
                        "line": node.lineno,
                        "message": f"High function complexity: '{node.name}()' exceeds 35 lines; consider refactoring",
                        "source": "Static Tool (AST Analysis)",
                        "confidence": "Medium"
                    })

            # 3. Wildcard imports
            if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
                issues.append({
                    "id": f"quality_{len(issues)+1}",
                    "type": "quality",
                    "severity": "low",
                    "file": filename,
                    "line": getattr(node, "lineno", 1),
                    "message": f"Wildcard import 'from {node.module} import *' pollutes the global namespace",
                    "source": "Static Tool (AST Analysis)",
                    "confidence": "High"
                })

    except Exception:
        pass
    return issues


def run_multilingual_regex_patterns(code: str, filename: str) -> list:
    """
    Universal pattern-based analyzer for JS/TS, Java, Go, C++, PHP, and config files.
    Ensures deterministic detection of hardcoded secrets, unsafe eval, and SQL concatenation.
    """
    issues = []
    lines = code.split("\n")
    suffix = Path(filename).suffix.lower()

    # Skip files that have dedicated AST parsers (Python handles these via Bandit/AST)
    if suffix in [".py", ".pyw"]:
        return issues

    for line_idx, line in enumerate(lines, start=1):
        clean_line = line.strip()

        # 1. Hardcoded API secrets / tokens across languages
        if re.search(r'(?:api_key|secret|password|auth_token|jwt_secret)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']', clean_line, re.IGNORECASE):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Hardcoded secret or credential token detected in source code",
                "cwe": "798",
                "source": "Static Pattern Analyzer",
                "confidence": "High"
            })

        # 2. JavaScript / TypeScript / PHP eval() or Function constructor
        if suffix in [".js", ".jsx", ".ts", ".tsx", ".php"] and re.search(r'\beval\s*\(', clean_line):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Unsafe eval() usage: processes arbitrary expressions without sanitization",
                "cwe": "95",
                "source": "Static Pattern Analyzer",
                "confidence": "High"
            })

        # 3. SQL string concatenation across languages
        if re.search(r'(?:select\s+.+\s+from|insert\s+into|delete\s+from)\s*.*\+\s*[A-Za-z0-9_]+', clean_line, re.IGNORECASE):
            issues.append({
                "id": f"sec_{len(issues)+1}",
                "type": "security",
                "severity": "high",
                "file": filename,
                "line": line_idx,
                "message": "Potential SQL Injection: direct string concatenation in SQL query",
                "cwe": "89",
                "source": "Static Pattern Analyzer",
                "confidence": "High"
            })

    return issues


def analyze_files(files: list) -> list:
    all_issues = []
    for file in files:
        filename = file.get("filename", "unknown.py")
        patch = file.get("patch", "")

        code = extract_added_code(patch)
        if not code or not code.strip():
            code = file.get("content", "")
            if not code or not code.strip():
                continue

        suffix = Path(filename).suffix.lower()

        # Python files -> Pyflakes, Bandit, AST
        if suffix in [".py", ".pyw"]:
            pyflakes_issues = run_pyflakes(code, filename)
            bandit_issues = run_bandit(code, filename)
            quality_issues = run_ast_quality_checks(code, filename)
            all_issues.extend(pyflakes_issues)
            all_issues.extend(bandit_issues)
            all_issues.extend(quality_issues)
        else:
            # Multilingual files (JS, TS, Java, Go, C++, PHP, etc.)
            pattern_issues = run_multilingual_regex_patterns(code, filename)
            all_issues.extend(pattern_issues)

    # Assign clean sequential integer IDs
    for idx, issue in enumerate(all_issues, start=1):
        issue["id"] = idx

    return all_issues


def extract_added_code(patch: str) -> str:
    lines = []
    for line in patch.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return "\n".join(lines)
