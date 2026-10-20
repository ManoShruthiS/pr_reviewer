# ==============================================================================
# FILE: language_detector.py
# PURPOSE: Identifies what programming language each file is written in,
#          and calculates how much of the project was analyzed (Coverage %).
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like a multilingual translator and sorting office:
# - If a file ends with ".py", this file shouts: "That's Python! Send it to Bandit & Pyflakes!"
# - If a file ends with ".js", this file shouts: "That's JavaScript! Check it for XSS and eval()!"
# - If a file ends with ".lock", this file says: "That's computer-generated junk! Skip it!"
# At the end, it tells you: "We analyzed 5 out of 5 files (100% coverage) across Python and JavaScript."
# ==============================================================================

# Path is a built-in Python tool that helps us easily inspect filenames and extensions (like .py, .js)
from pathlib import Path


# ------------------------------------------------------------------------------
# STEP 1: DICTIONARY OF KNOWN PROGRAMMING LANGUAGES
# ------------------------------------------------------------------------------
# This table maps file endings (extensions) to their real human name and tools.
LANGUAGE_MAP = {
    # --- Python Files ---
    ".py":  {"language": "Python", "category": "source_code", "has_static_tool": True, "static_tools": ["Bandit", "Pyflakes", "AST"]},
    ".pyw": {"language": "Python", "category": "source_code", "has_static_tool": True, "static_tools": ["Bandit", "Pyflakes", "AST"]},

    # --- JavaScript & TypeScript Files ---
    ".js":  {"language": "JavaScript", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".jsx": {"language": "JavaScript (React)", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".mjs": {"language": "JavaScript (ESM)", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".ts":  {"language": "TypeScript", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".tsx": {"language": "TypeScript (React)", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # --- Java & Kotlin Files ---
    ".java": {"language": "Java", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".kt":   {"language": "Kotlin", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # --- C & C++ Files ---
    ".c":   {"language": "C", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".h":   {"language": "C/C++ Header", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".cpp": {"language": "C++", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".hpp": {"language": "C++ Header", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".cc":  {"language": "C++", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # --- Go & Rust Files ---
    ".go": {"language": "Go", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".rs": {"language": "Rust", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # --- PHP & Ruby Files ---
    ".php": {"language": "PHP", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},
    ".rb":  {"language": "Ruby", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # --- C# (.NET) Files ---
    ".cs": {"language": "C#", "category": "source_code", "has_static_tool": True, "static_tools": ["Security Rules", "Pattern Analyzer"]},

    # --- Shell Scripts (Terminal Commands) ---
    ".sh":   {"language": "Shell", "category": "script", "has_static_tool": False, "static_tools": []},
    ".bash": {"language": "Bash", "category": "script", "has_static_tool": False, "static_tools": []},

    # --- Database Query Files ---
    ".sql": {"language": "SQL", "category": "database", "has_static_tool": False, "static_tools": []},

    # --- Web Page Design & Styling Files ---
    ".html": {"language": "HTML", "category": "markup", "has_static_tool": False, "static_tools": []},
    ".css":  {"language": "CSS", "category": "styling", "has_static_tool": False, "static_tools": []},
    ".scss": {"language": "SCSS", "category": "styling", "has_static_tool": False, "static_tools": []},

    # --- Configuration and Data Files ---
    ".json": {"language": "JSON", "category": "config", "has_static_tool": False, "static_tools": []},
    ".yaml": {"language": "YAML", "category": "config", "has_static_tool": False, "static_tools": []},
    ".yml":  {"language": "YAML", "category": "config", "has_static_tool": False, "static_tools": []},
    ".xml":  {"language": "XML", "category": "config", "has_static_tool": False, "static_tools": []},
    ".env":  {"language": "Env Config", "category": "config", "has_static_tool": False, "static_tools": []},

    # --- Reading Material & Documentation ---
    ".md":  {"language": "Markdown", "category": "documentation", "has_static_tool": False, "static_tools": []},
    ".txt": {"language": "Text", "category": "documentation", "has_static_tool": False, "static_tools": []},
}

# ------------------------------------------------------------------------------
# STEP 2: FILES WE DELIBERATELY IGNORE
# ------------------------------------------------------------------------------
# These are automatically generated lockfiles or giant bundled files.
# Humans don't write them, so reviewing them would just produce useless noise.
IGNORED_PATTERNS = [
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    ".min.js",
    ".min.css"
]


# ------------------------------------------------------------------------------
# STEP 3: FUNCTION TO DETECT A SINGLE FILE'S LANGUAGE
# ------------------------------------------------------------------------------
# Pass a filename like "backend/main.py", and this function figures out what it is.
def detect_file_info(filename: str) -> dict:
    """
    Detects language, category, and review strategy for a given file path.
    """
    # Use Path to extract the filename and suffix (e.g. ".py")
    path = Path(filename)
    name = path.name.lower()      # The filename in lowercase (e.g. "main.py")
    suffix = path.suffix.lower()  # Just the ending in lowercase (e.g. ".py")

    # Check if the file is one of our ignored files (like package-lock.json)
    for pat in IGNORED_PATTERNS:
        if name.endswith(pat) or pat in name:
            return {
                "filename": filename,
                "language": "Generated/Lockfile",
                "category": "generated",
                "is_analyzable": False,  # Don't scan this file
                "has_static_tool": False,
                "static_tools": [],
                "reason": "Lockfiles/minified assets are skipped from code review"
            }

    # Look up the extension in our known language dictionary
    info = LANGUAGE_MAP.get(suffix)
    if info:
        # If it's source code, script, database, or config, we definitely want to analyze it!
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

    # If the file extension is not in our dictionary, handle it safely as "Unknown"
    return {
        "filename": filename,
        "language": suffix.replace(".", "").upper() or "Unknown",
        "category": "unknown",
        "is_analyzable": True,  # We still let the AI look at it to be helpful
        "has_static_tool": False,
        "static_tools": [],
        "reason": "Unrecognized extension; review attempted via AI contextual reasoning"
    }


# ------------------------------------------------------------------------------
# STEP 4: FUNCTION TO CALCULATE PR COVERAGE ACROSS ALL FILES
# ------------------------------------------------------------------------------
# This counts:
# - How many total files exist in the Pull Request
# - How many files were successfully scanned
# - What languages were found (e.g. ['Python', 'HTML'])
# - Calculates the percentage: (Analyzed / Total) * 100
def analyze_pr_coverage(files: list) -> dict:
    """
    Generates transparent coverage statistics across all files in a PR.
    """
    total_files = len(files)  # Total number of files changed in the PR
    analyzed_count = 0        # Counter for files we actually reviewed
    languages = set()         # Set to store unique languages found (no duplicates)
    tools_used = set()        # Set to store tools we ran (e.g. Bandit, Pyflakes)
    file_breakdown = []       # Detailed list of each individual file's status

    # Loop through each file in the PR
    for file in files:
        fname = file.get("filename", "")
        # Inspect this file's language and tools
        finfo = detect_file_info(fname)
        languages.add(finfo["language"])

        method = []
        # If this file has specialized static security tools (like Bandit for Python), record them
        if finfo["has_static_tool"]:
            method.extend(finfo["static_tools"])
            tools_used.update(finfo["static_tools"])

        # If the file is analyzable code, count it as analyzed
        if finfo["is_analyzable"]:
            method.append("AI Reviewer")
            tools_used.add("AI Contextual Review")
            analyzed_count += 1
            status = "Analyzed"
        else:
            status = "Skipped"

        # Record this file in the breakdown report
        file_breakdown.append({
            "filename": fname,
            "language": finfo["language"],
            "category": finfo["category"],
            "status": status,
            "methods": method,
            "reason": finfo.get("reason")
        })

    # Calculate the percentage of files analyzed (e.g. 5 out of 5 = 100.0%)
    coverage_percent = round((analyzed_count / total_files * 100), 1) if total_files > 0 else 100.0

    # Return the complete summary report
    return {
        "total_files": total_files,
        "analyzed_files": analyzed_count,
        "skipped_files": total_files - analyzed_count,
        "coverage_percentage": coverage_percent,
        "languages_detected": sorted(list(languages)),
        "tools_engaged": sorted(list(tools_used)),
        "file_breakdown": file_breakdown
    }
