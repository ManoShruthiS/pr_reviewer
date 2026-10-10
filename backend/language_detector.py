"""
Language Detector Module
Identifies programming languages and content categories from file extensions and names.
Fulfills FR-04 (Multilingual analysis) of the PR-Doc First Demo Specification.
"""

from pathlib import Path

# Mapping of file extensions to language definitions and capabilities
LANGUAGE_MAP = {
    # Python
    ".py": {"language": "Python", "category": "source_code", "has_static_tool": True, "static_tools": ["Bandit", "Pyflakes", "AST"]},
    ".pyw": {"language": "Python", "category": "source_code", "has_static_tool": True, "static_tools": ["Bandit", "Pyflakes", "AST"]},

    # JavaScript / TypeScript
    ".js": {"language": "JavaScript", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".jsx": {"language": "JavaScript (React)", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".mjs": {"language": "JavaScript (ESM)", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".ts": {"language": "TypeScript", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".tsx": {"language": "TypeScript (React)", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # Java / Kotlin
    ".java": {"language": "Java", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".kt": {"language": "Kotlin", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # C / C++
    ".c": {"language": "C", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".h": {"language": "C/C++ Header", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".cpp": {"language": "C++", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".hpp": {"language": "C++ Header", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".cc": {"language": "C++", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # Go
    ".go": {"language": "Go", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # Rust
    ".rs": {"language": "Rust", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # PHP & Ruby
    ".php": {"language": "PHP", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".rb": {"language": "Ruby", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # C#
    ".cs": {"language": "C#", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # Shell
    ".sh": {"language": "Shell", "category": "script", "has_static_tool": False, "static_tools": []},
    ".bash": {"language": "Bash", "category": "script", "has_static_tool": False, "static_tools": []},

    # SQL
    ".sql": {"language": "SQL", "category": "database", "has_static_tool": False, "static_tools": []},

    # Web Markup & Styling
    ".html": {"language": "HTML", "category": "markup", "has_static_tool": False, "static_tools": []},
    ".css": {"language": "CSS", "category": "styling", "has_static_tool": False, "static_tools": []},
    ".scss": {"language": "SCSS", "category": "styling", "has_static_tool": False, "static_tools": []},

    # Configurations & Data
    ".json": {"language": "JSON", "category": "config", "has_static_tool": False, "static_tools": []},
    ".yaml": {"language": "YAML", "category": "config", "has_static_tool": False, "static_tools": []},
    ".yml": {"language": "YAML", "category": "config", "has_static_tool": False, "static_tools": []},
    ".xml": {"language": "XML", "category": "config", "has_static_tool": False, "static_tools": []},
    ".env": {"language": "Env Config", "category": "config", "has_static_tool": False, "static_tools": []},

    # Documentation & Markdown
    ".md": {"language": "Markdown", "category": "documentation", "has_static_tool": False, "static_tools": []},
    ".txt": {"language": "Text", "category": "documentation", "has_static_tool": False, "static_tools": []},
}

IGNORED_PATTERNS = [
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    ".min.js",
    ".min.css"
]


def detect_file_info(filename: str) -> dict:
    """
    Detects language, category, and review strategy for a given file path.
    """
    path = Path(filename)
    name = path.name.lower()
    suffix = path.suffix.lower()

    # Check for generated / lock files
    for pat in IGNORED_PATTERNS:
        if name.endswith(pat) or pat in name:
            return {
                "filename": filename,
                "language": "Generated/Lockfile",
                "category": "generated",
                "is_analyzable": False,
                "has_static_tool": False,
                "static_tools": [],
                "reason": "Lockfiles/minified assets are skipped from code review"
            }

    info = LANGUAGE_MAP.get(suffix)
    if info:
        is_code = info["category"] in ["source_code", "script", "database", "config"]
        return {
            "filename": filename,
            "language": info["language"],
            "category": info["category"],
            "is_analyzable": is_code,
            "has_static_tool": info["has_static_tool"],
            "static_tools": info["static_tools"],
            "reason": None
        }

    # Unknown or unsupported file type
    return {
        "filename": filename,
        "language": suffix.replace(".", "").upper() or "Unknown",
        "category": "unknown",
        "is_analyzable": True,  # Allow AI to attempt contextual review
        "has_static_tool": False,
        "static_tools": [],
        "reason": "Unrecognized extension; review attempted via AI contextual reasoning"
    }


def analyze_pr_coverage(files: list) -> dict:
    """
    Generates transparent coverage statistics across all files in a PR (FR-12).
    """
    total_files = len(files)
    analyzed_count = 0
    languages = set()
    tools_used = set()
    file_breakdown = []

    for file in files:
        fname = file.get("filename", "")
        finfo = detect_file_info(fname)
        languages.add(finfo["language"])

        method = []
        if finfo["has_static_tool"]:
            method.extend(finfo["static_tools"])
            tools_used.update(finfo["static_tools"])

        if finfo["is_analyzable"]:
            method.append("AI Reviewer")
            tools_used.add("AI Contextual Review")
            analyzed_count += 1
            status = "Analyzed"
        else:
            status = "Skipped"

        file_breakdown.append({
            "filename": fname,
            "language": finfo["language"],
            "category": finfo["category"],
            "status": status,
            "methods": method,
            "reason": finfo.get("reason")
        })

    coverage_percent = round((analyzed_count / total_files * 100), 1) if total_files > 0 else 100.0

    return {
        "total_files": total_files,
        "analyzed_files": analyzed_count,
        "skipped_files": total_files - analyzed_count,
        "coverage_percentage": coverage_percent,
        "languages_detected": sorted(list(languages)),
        "tools_engaged": sorted(list(tools_used)),
        "file_breakdown": file_breakdown
    }
