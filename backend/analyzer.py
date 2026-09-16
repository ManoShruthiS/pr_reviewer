import ast
import io
import subprocess
import tempfile
import os


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
                    "type": "bug",
                    "severity": "medium",
                    "file": filename,
                    "line": lineno,
                    "message": f"Syntax error: {message}"
                })

            def flake(self, message):
                severity = "low"
                msg_str = str(message)
                if "undefined name" in msg_str.lower() or "used before assignment" in msg_str.lower():
                    severity = "medium"
                self.messages.append({
                    "type": "bug",
                    "severity": severity,
                    "file": filename,
                    "line": message.lineno,
                    "message": msg_str.split(": ", 1)[-1] if ": " in msg_str else msg_str
                })

        reporter = Collector()
        pyflakes.api.check(code, filename, reporter)
        issues.extend(reporter.messages)
    except SyntaxError as e:
        issues.append({
            "type": "bug",
            "severity": "high",
            "file": filename,
            "line": e.lineno or 0,
            "message": f"Syntax error: {e.msg}"
        })
    return issues


def run_bandit(code: str, filename: str) -> list:
    issues = []
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", temp_path],
            capture_output=True, text=True
        )
        if result.stdout:
            import json
            data = json.loads(result.stdout)
            for item in data.get("results", []):
                severity = item.get("issue_severity", "LOW").lower()
                issues.append({
                    "type": "security",
                    "severity": severity,
                    "file": filename,
                    "line": item.get("line_number", 0),
                    "message": item.get("issue_text", ""),
                    "cwe": item.get("issue_cwe", {}).get("id", "")
                })
    except Exception:
        pass
    finally:
        os.unlink(temp_path)

    return issues


def analyze_files(files: list) -> list:
    all_issues = []
    for file in files:
        filename = file["filename"]
        patch = file["patch"]

        code = extract_added_code(patch)
        if not code:
            continue

        all_issues.extend(run_pyflakes(code, filename))
        all_issues.extend(run_bandit(code, filename))

    return all_issues


def extract_added_code(patch: str) -> str:
    lines = []
    for line in patch.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return "\n".join(lines)
