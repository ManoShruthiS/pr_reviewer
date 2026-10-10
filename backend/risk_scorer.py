def calculate_risk_score(issues: list) -> int:
    """
    Computes an authentic, defensible risk score from 0 to 100.
    - Security vulnerabilities (CWE/CVEs): major risk driver (10-35 pts)
    - Functional bugs & exceptions: moderate-high risk driver (5-25 pts)
    - Quality & maintainability smells (unused imports, line count): minor risk (2-8 pts)
    """
    if not issues:
        return 0

    score = 0
    for issue in issues:
        severity = issue.get("severity", "low").lower()
        itype = issue.get("type", "quality").lower()

        if itype == "security":
            if severity in ["critical", "high"]:
                score += 35
            elif severity == "medium":
                score += 20
            else:
                score += 10
        elif itype == "bug":
            if severity in ["critical", "high"]:
                score += 25
            elif severity == "medium":
                score += 15
            else:
                score += 6
        else:
            # Code quality (code smells, maintainability, formatting)
            if severity in ["critical", "high"]:
                score += 8
            elif severity == "medium":
                score += 4
            else:
                score += 2

    return min(score, 100)

